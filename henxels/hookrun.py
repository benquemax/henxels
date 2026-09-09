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
from henxels.diffinfo import staged_diff
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


def _digest_drift(contract, root: Path) -> list[Finding]:
    """Warn (loudly, never block) when the AGENTS.md digest is stale relative to
    the contract — the mirrored rules agents read must not silently lie after a
    henxels.yaml edit that was never `henxels sync`'d. Only fires when an
    AGENTS.md digest already exists; a repo that doesn't mirror is left alone."""
    from henxels.digest import check_file
    from henxels.findings import WARN

    target = root / "AGENTS.md"
    if check_file(target, contract) != "stale":
        return []
    return [Finding(
        level=WARN,
        henxel="The AGENTS.md digest mirrors the contract — keep it in sync",
        path="AGENTS.md",
        message="AGENTS.md is out of date with henxels.yaml",
        details=["agents read the mirrored digest, not the YAML — a stale digest lies to them"],
        steer="henxels sync   (then commit AGENTS.md too)",
    )]


def _schema_drift(root: Path) -> list[Finding]:
    """Warn (loudly, never block) when the repo's committed schema copy predates the
    installed henxels. Distinct from the "stale tool" nag: there the tool is behind,
    here the tool is current and the repo's copy of its documentation is behind — and
    that copy is what a reader trusts when deciding whether a knob exists. Only fires
    when a local copy exists; a repo that keeps none is left alone."""
    from henxels import __version__
    from henxels.findings import WARN
    from henxels.schema import LOCAL_SCHEMA_PATH, local_schema_state

    if local_schema_state(root) != "stale":
        return []
    return [Finding(
        level=WARN,
        henxel="The bundled editor schema mirrors the installed henxels — keep it in sync",
        path=LOCAL_SCHEMA_PATH,
        message=f"{LOCAL_SCHEMA_PATH} predates the installed henxels ({__version__})",
        details=["a schema older than the tool hides knobs that already work — "
                 "readers trust the committed artifact over the binary"],
        steer="henxels init   (or `henxels sync`) — then commit the refreshed schema",
    )]


def run_precommit(root: Path | str, now: float | None = None) -> tuple[int, list[Finding]]:
    root = Path(root)
    contract = _load(root)
    if contract is None:
        return 0, []

    findings: list[Finding] = run_contract(contract, root, diff=staged_diff(root))

    findings.extend(_digest_drift(contract, root))
    findings.extend(_schema_drift(root))

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
