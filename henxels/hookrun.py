"""What the installed git hooks run (v2).

pre-commit → structure check (run the contract) + similarity warnings + delete
             protection + pre_commit command gates (tests, lints).
pre-push   → pre_push command gates + push protection.

Tokens are spent only when the action actually proceeds.
"""

from __future__ import annotations

from pathlib import Path

from henxels import bless, settings
from henxels.commands import run_commands
from henxels.contract import ContractError, apply_imports, find_contract, load_contract
from henxels.engine import gitinfo
from henxels.findings import Finding
from henxels.guard import collect_deletions, deletion_finding, push_finding
from henxels.runner import run_contract, stage_commands


def _load(root: Path):
    path = find_contract(root)
    if path is None:
        return None
    try:
        contract = load_contract(path)
    except ContractError:
        return None
    apply_imports(contract, root=root)
    return contract


def run_precommit(root: Path | str, now: float | None = None) -> tuple[int, list[Finding]]:
    root = Path(root)
    contract = _load(root)
    if contract is None:
        return 0, []

    findings: list[Finding] = run_contract(contract, root)

    sim = settings.similarity(contract)
    if sim:
        from henxels.similarity import warn_similar

        findings.extend(warn_similar(sim, root, gitinfo.staged_files(root)))

    large = settings.large_files(contract)
    if large:
        from henxels.filesize import warn_large_files

        findings.extend(warn_large_files(large, root, gitinfo.staged_files(root)))

    deletions = None
    dp = settings.delete_protection(contract)
    if dp:
        deletions = collect_deletions(root, dp["over_lines"])
        if not deletions.empty and not bless.is_blessed(root, "delete", deletions.fingerprint(), now=now):
            findings.append(deletion_finding(deletions))

    # Run command gates only if nothing already blocks (fast feedback; don't burn a bless).
    if not any(f.is_block for f in findings):
        findings.extend(run_commands(stage_commands(contract, "pre_commit"), "pre_commit", root))

    blocks = sum(1 for f in findings if f.is_block)
    if blocks == 0 and dp and deletions is not None and not deletions.empty:
        bless.consume(root, "delete", deletions.fingerprint(), now=now)

    return (1 if blocks else 0, findings)


def run_prepush(root: Path | str, now: float | None = None) -> tuple[int, list[Finding]]:
    root = Path(root)
    contract = _load(root)
    if contract is None:
        return 0, []

    findings = run_commands(stage_commands(contract, "pre_push"), "pre_push", root)
    if any(f.is_block for f in findings):
        return 1, findings

    if not settings.confirm_before_push(contract):
        return 0, findings

    fingerprint = gitinfo.head_sha(root) or "no-head"
    if bless.consume(root, "push", fingerprint, now=now):
        return 0, findings
    return 1, findings + [push_finding()]
