"""What the installed git hooks actually run.

``pre-commit`` → structure check on staged files + the delete guard.
``pre-push``   → the push guard.

Tokens are only *spent* when the action is actually allowed, so a commit blocked by
a structure henxel doesn't burn a delete bless.
"""

from __future__ import annotations

from pathlib import Path

from henxels import bless
from henxels.checker import check_paths
from henxels.checks import run_checks
from henxels.config.load import ConfigError, find_config, load_config
from henxels.engine import gitinfo
from henxels.findings import Finding
from henxels.rules.guard import (
    collect_deletions,
    deletion_finding,
    guard_mode,
    push_finding,
)


def _load(root: Path):
    path = find_config(root)
    if path is None:
        return None
    try:
        return load_config(path)
    except ConfigError:
        return None


def run_precommit(root: Path | str, now: float | None = None) -> tuple[int, list[Finding]]:
    """Return (exit_code, findings) for the pre-commit hook."""
    root = Path(root)
    config = _load(root)
    if config is None:
        return 0, []  # no contract → don't get in the way

    findings: list[Finding] = []
    staged = gitinfo.staged_files(root)
    findings.extend(check_paths(config, root, staged, check_existence=False))

    deletions = None
    delete_active = guard_mode(config, "delete") == "bless"
    if delete_active:
        deletions = collect_deletions(config, root)
        if not deletions.empty and not bless.is_blessed(
            root, "delete", deletions.fingerprint(), now=now
        ):
            findings.append(deletion_finding(deletions))

    # Run contract checks (e.g. the test suite) only if nothing already blocks —
    # faster feedback, and we won't spend a delete bless on a doomed commit.
    if not any(f.is_block for f in findings):
        findings.extend(run_checks(config, "pre_commit", root))

    blocks = sum(1 for f in findings if f.is_block)

    # Spend the delete token only if the commit is actually going through.
    if blocks == 0 and delete_active and deletions is not None and not deletions.empty:
        bless.consume(root, "delete", deletions.fingerprint(), now=now)

    return (1 if blocks else 0, findings)


def run_prepush(root: Path | str, now: float | None = None) -> tuple[int, list[Finding]]:
    """Return (exit_code, findings) for the pre-push hook."""
    root = Path(root)
    config = _load(root)
    if config is None:
        return 0, []

    # Contract checks first — never spend a push bless on a failing push.
    check_findings = run_checks(config, "pre_push", root)
    if any(f.is_block for f in check_findings):
        return 1, check_findings

    if guard_mode(config, "push") != "bless":
        return (0, check_findings)

    fingerprint = gitinfo.head_sha(root) or "no-head"
    if bless.consume(root, "push", fingerprint, now=now):
        return 0, check_findings
    return 1, check_findings + [push_finding()]
