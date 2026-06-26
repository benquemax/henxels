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
from henxels.findings import Finding
from henxels.statements.registry import StatementDef, get_statement
from henxels.statements.scope import Scope, build_scope


def run_contract(contract: Contract, root: Path | str, files: list[str] | None = None) -> list[Finding]:
    root = Path(root)
    all_files = files if files is not None else discover(root)

    findings: list[Finding] = []
    for hx in contract.henxels:
        scope = build_scope(hx.locations, all_files, root, contract.settings)
        instructions: list[str] = []
        for name, param in hx.statements.items():
            sdef = get_statement(name)
            if sdef is None:
                instructions.append(f"unknown check '{name}' — import the module that defines it")
                continue
            if sdef.stage is not None:
                continue  # command gate; runs in the hooks
            instructions.extend(_invoke(sdef, param, scope, hx.text))

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


def _invoke(sdef: StatementDef, param, scope: Scope, sentence: str) -> list[str]:
    avail = {"param": param, "scope": scope, "root": scope.root, "settings": scope.settings}

    def call(extra=None):
        args = {**avail, **(extra or {})}
        try:
            return sdef.fn(*[args[p] for p in sdef.params])
        except Exception as exc:  # noqa: BLE001 - a broken check shouldn't crash the run
            return f"check '{sdef.name}' errored: {exc}"

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


def stage_commands(contract: Contract, stage: str) -> list[str]:
    """Collect command-gate commands for a git stage (pre_commit/pre_push)."""
    commands: list[str] = []
    for hx in contract.henxels:
        for name, param in hx.statements.items():
            sdef = get_statement(name)
            if sdef is not None and sdef.stage == stage:
                commands.extend(param if isinstance(param, list) else [param])
    return commands
