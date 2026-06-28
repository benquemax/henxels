"""Render the contract as a plain-language digest, and sync it into AGENTS.md.

The digest is what an agent reads: the rule list in plain words, the behaviours, and
a short note encouraging custom henxels and contribution of reusable ones. henxels
owns a marked block; text a human writes around it is left untouched.
"""

from __future__ import annotations

from pathlib import Path

from henxels.contract import Contract

BEGIN = "<!-- henxels:begin -->"
END = "<!-- henxels:end -->"


def render_digest(contract: Contract) -> str:
    lines: list[str] = [
        "## The contract (henxels)",
        "",
        "_Auto-generated from `henxels.yaml` by `henxels sync`. Do not edit by hand._",
        "",
        "Each bullet is a **henxel** (a rule). To disobey one, change `henxels.yaml` —",
        "that is the only sanctioned escape. Run `henxels explain <path>` before creating",
        "a file to see what governs that spot.",
        "",
    ]
    if contract.settings.get("ask_me_before_staging"):
        # Git can't be hooked before `git add`, so this lives or dies on being read.
        # Make it loud and imperative, and put it up top — small models skim the rest.
        lines += [
            "> **Git etiquette — important.** Do **not** run `git add`, `git commit`, or "
            "`git push` yourself in this repo. When your work is ready, stop and ask the user "
            "to review the diff and stage it. Staging on the user's behalf is a mistake here, "
            "even if the change looks correct.",
            ">",
            "> _OpenCode agents:_ run `henxels integrate opencode` once to make this **enforced** "
            "(it hard-blocks `git add`/`git commit`), not just advisory.",
            "",
        ]
    lines += [
        "### Rules",
        "",
    ]
    for hx in contract.henxels:
        tag = " _(warn)_" if hx.level == "warn" else ""
        where = "" if hx.locations in ([], ["./*"]) else f" (in {', '.join(hx.locations)})"
        lines.append(f"- {hx.text}{where}{tag}")
        if hx.why:
            lines.append(f"  ↳ {' '.join(hx.why.split())}")  # the reasoning, for the agent

    behaviours = _render_settings(contract)
    if behaviours:
        lines += ["", "### Behaviours", ""] + behaviours

    lines += [
        "",
        "### Custom henxels & contributing",
        "",
        "**Before writing a custom check, run `henxels catalogue` and use the built-in that",
        "matches your intent — don't reinvent one.** Never name a custom check after a built-in",
        "or a setting (e.g. `warn_about_large_files` is a setting, not a check).",
        "",
        "Need a check that genuinely doesn't exist? `henxels create-new-statement <name>` scaffolds a local check",
        "(auto-loaded from `henxels_checks.py`). **If your check is reusable** — useful in",
        "other repos, not tied to this one — contribute it upstream with `henxels contribute`.",
        "We're in the agentic era: send a ready-to-merge PR instead of opening an issue.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _render_settings(contract: Contract) -> list[str]:
    s = contract.settings
    out = []
    if s.get("ask_me_before_staging"):
        out.append("- **never `git add` / `git commit` / `git push` yourself** — ask the user to review and stage")
    if s.get("confirm_before_push"):
        out.append("- push is blocked until `henxels bless push`")
    if s.get("confirm_before_deleting"):
        out.append("- deleting files / removing many lines is blocked until `henxels bless delete`")
    if s.get("warn_about_similar_files"):
        out.append("- warns when a new file looks like a near-copy of a committed one")
    return out


def update_block(text: str, digest: str) -> str:
    block = f"{BEGIN}\n{digest.rstrip()}\n{END}"
    if BEGIN in text and END in text:
        pre = text[: text.index(BEGIN)]
        post = text[text.index(END) + len(END):]
        return pre + block + post
    if text and not text.endswith("\n"):
        text += "\n"
    if text:
        text += "\n"
    return text + block + "\n"


def sync_file(path: Path | str, contract: Contract) -> str:
    path = Path(path)
    existed = path.is_file()
    text = path.read_text(encoding="utf-8") if existed else ""
    path.write_text(update_block(text, render_digest(contract)), encoding="utf-8")
    return "updated" if existed else "created"
