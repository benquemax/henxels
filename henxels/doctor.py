"""`henxels doctor` — is the contract valid and the plumbing wired?"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from henxels.contract import ContractError, apply_imports, find_contract, load_contract
from henxels.engine.gitinfo import is_git_repo, shadowing_hooks_path
from henxels.hooks import HOOKS, hooks_status
from henxels.statements.registry import all_statements


@dataclass
class Check:
    ok: bool
    label: str
    detail: str = ""


def diagnose(root: Path | str) -> list[Check]:
    root = Path(root)
    checks: list[Check] = []

    git = is_git_repo(root)
    checks.append(Check(git, "git repository", "" if git else "guards/similarity need git"))

    path = find_contract(root)
    if path is None:
        checks.append(Check(False, "contract found", "run `henxels init`"))
        return checks
    checks.append(Check(True, "contract found", path.name))

    try:
        contract = load_contract(path)
        checks.append(Check(True, "contract parses", f"{len(contract.henxels)} henxels"))
    except ContractError as exc:
        checks.append(Check(False, "contract parses", str(exc)))
        return checks

    failed = apply_imports(contract, root=root)
    checks.append(Check(not failed, "custom imports", ", ".join(failed) if failed else "ok"))

    # Every statement referenced by the contract must be registered.
    known = set(all_statements())
    referenced = {name for hx in contract.henxels for name in hx.statements}
    missing = sorted(referenced - known)
    checks.append(Check(not missing, "statements resolve", ", ".join(missing) if missing else "all known"))

    # Custom checks that reinvent a built-in (or use a settings name) — the common
    # small-model mistake. Surface it so it gets fixed, not silently shadowed.
    from henxels.statements.registry import custom_collisions

    collisions = custom_collisions()
    checks.append(Check(not collisions, "custom checks", "ok" if not collisions else "; ".join(collisions)))

    # markdown_lint is a no-op without its optional dependency — surface that here so a
    # missing linter is a visible setup nudge, not a silently-skipped check.
    if "markdown_lint" in referenced:
        from henxels.statements.builtins.content import pymarkdown_available

        avail = pymarkdown_available()
        checks.append(
            Check(avail, "markdown_lint ready", "" if avail else "install pymarkdownlnt (e.g. `henxels[markdown]`)")
        )

    if git:
        # henxels installs into .git/hooks — but if core.hooksPath (husky, lefthook, …)
        # points elsewhere, git ignores .git/hooks and our hooks never run. Report the
        # truth, not a misleading green.
        shadowed = shadowing_hooks_path(root)
        for hook, present in hooks_status(root).items():
            if present and not shadowed:
                checks.append(Check(True, f"hook: {hook}"))
            elif present and shadowed:
                checks.append(
                    Check(
                        False,
                        f"hook: {hook}",
                        f"core.hooksPath={shadowed} shadows .git/hooks — henxels won't run; "
                        f"unset it, or call `henxels {HOOKS[hook]}` from that {hook} hook",
                    )
                )
            else:
                checks.append(Check(False, f"hook: {hook}", "run `henxels init`"))

    agents = root / "AGENTS.md"
    has_digest = agents.is_file() and "henxels:begin" in agents.read_text(encoding="utf-8", errors="replace")
    checks.append(Check(has_digest, "AGENTS.md digest", "" if has_digest else "run `henxels sync`"))

    return checks
