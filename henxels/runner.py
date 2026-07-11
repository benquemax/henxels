"""Run a contract: every henxel is a test; collect the ones that don't pass.

For each henxel we build its scope from ``in:``, invoke each statement with
name-injected arguments, and gather instructions. A henxel with any instruction
becomes one Finding whose header is the henxel's sentence and whose details are the
per-file instructions. Command-gate statements are skipped here (the hooks run them).
"""

from __future__ import annotations

from pathlib import Path

from henxels.contract import Contract
from henxels.engine.discover import discover
from henxels.findings import BLOCK, Finding
from henxels.statements.registry import StatementDef, get_statement
from henxels.statements.scope import Scope, build_scope
from henxels.version_check import requirement_unmet


def run_contract(
    contract: Contract, root: Path | str, files: list[str] | None = None, diff=None
) -> list[Finding]:
    root = Path(root)

    # Version floor first: if the contract declares it needs a newer henxels than this
    # one, say so once — clearly — instead of letting every newer check fail cryptically.
    unmet = requirement_unmet(contract.requires)
    if unmet:
        return [
            Finding(
                level=BLOCK,
                henxel="This contract requires a newer henxels",
                path="",
                message="",
                details=[unmet],
                steer="upgrade henxels, or lower requires_henxels in henxels.yaml",
            )
        ]

    all_files = files if files is not None else discover(root)

    findings: list[Finding] = []
    for hx in contract.henxels:
        scope = build_scope(hx.locations, all_files, root, contract.settings, hx.excludes)
        instructions: list[str] = []
        for name, param in hx.statements.items():
            sdef = get_statement(name)
            if sdef is None:
                instructions.append(
                    f"unknown check '{name}' — if it's a newer built-in, upgrade henxels "
                    f"(you're on {_running_version()}); if it's a custom check, import the "
                    f"module that defines it"
                )
                continue
            if sdef.stage is not None:
                continue  # command gate; runs in the hooks
            instructions.extend(_invoke(sdef, param, scope, hx.text, diff))

        if instructions:
            findings.append(
                Finding(
                    level=hx.level,
                    henxel=hx.text,
                    path="",
                    message="",
                    details=instructions,
                    steer="change this henxel in henxels.yaml to allow it",
                )
            )
    return findings


def _invoke(sdef: StatementDef, param, scope: Scope, sentence: str, diff=None) -> list[str]:
    avail = {"param": param, "scope": scope, "root": scope.root, "settings": scope.settings, "diff": diff}

    def call(extra=None):
        args = {**avail, **(extra or {})}
        try:
            return sdef.fn(*[args[p] for p in sdef.params])
        except Exception as exc:  # noqa: BLE001 - a broken check shouldn't crash the run
            return (
                f"check '{sdef.name}' errored: {exc} — often a version skew "
                f"(you're on henxels {_running_version()}); if the contract uses newer "
                f"syntax, upgrading may fix it"
            )

    out: list[str] = []
    if sdef.per_file:
        for f in scope.files:
            out.extend(_normalize(call({"file": f}), file=f, sentence=sentence))
    else:
        out.extend(_normalize(call(), file=None, sentence=sentence))
    return out


def _normalize(result, file: str | None, sentence: str) -> list[str]:
    """Turn a statement's return into a list of actionable instruction strings."""
    if result is None or result is True:
        return []
    if result is False:
        return [f"{file} — {sentence}" if file else sentence]
    if isinstance(result, str):
        return [_with_file(result, file)]
    if isinstance(result, (list, tuple)):
        out: list[str] = []
        for item in result:
            out.extend(_normalize(item, file, sentence))
        return out
    return []  # ignore anything else


def _with_file(message: str, file: str | None) -> str:
    if file and file not in message:
        return f"{file} — {message}"
    return message


def _running_version() -> str:
    from henxels import __version__  # lazy: avoids an import cycle at module load

    return __version__


def stage_commands(contract: Contract, stage: str) -> list[str]:
    """Collect command-gate commands for a git stage (pre_commit/pre_push)."""
    commands: list[str] = []
    for hx in contract.henxels:
        for name, param in hx.statements.items():
            sdef = get_statement(name)
            if sdef is not None and sdef.stage == stage:
                commands.extend(param if isinstance(param, list) else [param])
    return commands
