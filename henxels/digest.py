"""Render the contract as a plain-language digest, and keep it synced into AGENTS.md.

The digest is what an agent reads. It must say, in words a small model can act on:
where things go, what must exist, and how to disobey responsibly (edit the contract).
henxels owns a marked block; everything a human writes around it is left untouched.
"""

from __future__ import annotations

from pathlib import Path

from henxels.config.load import Config
from henxels.config.tree import RULE_KEYS

BEGIN = "<!-- henxels:begin -->"
END = "<!-- henxels:end -->"


def render_digest(config: Config) -> str:
    """Build the plain-language contract digest (markdown, no surrounding markers)."""
    lines: list[str] = [
        "## Structure contract (henxels)",
        "",
        "_Auto-generated from `henxels.yaml` by `henxels sync`. Do not edit by hand._",
        "",
        "Put the right thing in the right place. The **closest rule in the tree wins**.",
        "To disobey a rule, change `henxels.yaml` — that is the only sanctioned escape.",
        "Run `henxels explain <path>` before creating a file to see what governs that spot.",
        "",
    ]

    tree_lines = _render_tree(config.tree)
    if tree_lines:
        lines.append("### Where things live")
        lines.append("")
        lines.extend(tree_lines)
        lines.append("")

    guard_lines = _render_guards(config)
    if guard_lines:
        lines.append("### Guards")
        lines.append("")
        lines.extend(guard_lines)
        lines.append("")

    canon_lines = _render_canonical(config)
    if canon_lines:
        lines.append("### Single source of truth")
        lines.append("")
        lines.extend(canon_lines)
        lines.append("")

    require_lines = _render_require(config)
    if require_lines:
        lines.append("### Must exist")
        lines.append("")
        lines.extend(require_lines)
        lines.append("")

    check_lines = _render_checks(config)
    if check_lines:
        lines.append("### Checks run by the hooks")
        lines.append("")
        lines.extend(check_lines)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _render_require(config: Config) -> list[str]:
    out: list[str] = []
    for entry in config.require:
        spec = entry if isinstance(entry, dict) else {"file": entry}
        file = spec.get("file", "?")
        note = f" — {spec['reason']}" if spec.get("reason") else ""
        tag = " _(warn)_" if str(spec.get("severity", "")).lower() == "warn" else ""
        out.append(f"- `{file}`{note}{tag}")
    return out


def _render_checks(config: Config) -> list[str]:
    out: list[str] = []
    for stage in ("pre_commit", "pre_push"):
        cmds = config.checks.get(stage)
        if not cmds:
            continue
        cmds = [cmds] if isinstance(cmds, str) else cmds
        joined = ", ".join(f"`{c}`" for c in cmds)
        out.append(f"- **{stage}**: {joined}")
    return out


def _render_tree(tree: dict, prefix: str = "", depth: int = 0) -> list[str]:
    if not isinstance(tree, dict):
        return []
    out: list[str] = []
    indent = "  " * depth
    for key, node in tree.items():
        if key in RULE_KEYS or not isinstance(node, dict):
            continue
        path = f"{prefix}/{key}" if prefix else key
        bits: list[str] = []
        if isinstance(node.get("naming"), str):
            bits.append(f"files are {node['naming']}")
        if isinstance(node.get("mirror"), str):
            bits.append(f"mirrors `{node['mirror']}`")
        if isinstance(node.get("purpose"), str):
            bits.append(node["purpose"])
        suffix = f" — {', '.join(bits)}" if bits else ""
        out.append(f"{indent}- `{path}/`{suffix}")

        for entry in _as_list(node.get("forbid")):
            spec = entry if isinstance(entry, dict) else {"glob": entry}
            reason = f": {spec['reason']}" if spec.get("reason") else ""
            steer = f" → {spec['steer']}" if spec.get("steer") else ""
            out.append(f"{indent}  - forbid `{spec.get('glob', '?')}`{reason}{steer}")
        for entry in _as_list(node.get("require")):
            spec = entry if isinstance(entry, dict) else {"file": entry}
            reason = f" ({spec['reason']})" if spec.get("reason") else ""
            out.append(f"{indent}  - must contain `{spec.get('file', '?')}`{reason}")

        out.extend(_render_tree(node, path, depth + 1))
    return out


def _render_guards(config: Config) -> list[str]:
    out: list[str] = []
    for action in ("push", "commit", "stage", "delete"):
        raw = config.guards.get(action)
        if raw is None:
            continue
        mode = raw.get("mode", "off") if isinstance(raw, dict) else raw
        if mode == "off":
            continue
        if mode == "ask":
            out.append(f"- **{action}**: ask the user first (don't do it reflexively)")
        elif action == "delete":
            thr = raw.get("line_threshold", 5) if isinstance(raw, dict) else 5
            out.append(
                f"- **delete**: deleting files or removing >{thr} lines is blocked "
                "until `henxels bless delete`"
            )
        else:
            out.append(f"- **{action}**: blocked until `henxels bless {action}`")
    return out


def _render_canonical(config: Config) -> list[str]:
    out: list[str] = []
    for entry in config.canonical:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role") or "this"
        file = entry.get("file", "?")
        line = f"- {role} lives only in `{file}`"
        looks = entry.get("forbid_lookalikes")
        if looks:
            line += f" — don't create {', '.join(f'`{x}`' for x in looks)}"
        out.append(line)
    return out


def update_block(text: str, digest: str) -> str:
    """Replace the henxels-managed block in ``text`` with ``digest`` (or append it)."""
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


def sync_file(path: Path | str, config: Config) -> str:
    """Write/refresh the digest block in ``path``. Returns 'created'|'updated'."""
    path = Path(path)
    existed = path.is_file()
    text = path.read_text(encoding="utf-8") if existed else ""
    new_text = update_block(text, render_digest(config))
    path.write_text(new_text, encoding="utf-8")
    return "updated" if existed else "created"


def _as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]
