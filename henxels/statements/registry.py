"""The statement registry — what makes henxels extensible.

A *statement* is a named function that verifies one thing. Authoring is boilerplate-
free: arguments are injected **by name** (pytest-style), and failure is expressed as
an **instruction**, so the result is actionable for a small model — not a bare bool.

Inject any of these by naming them as parameters (take only what you need):

    param      the value from the contract (e.g. 500 for ``max_lines: 500``)
    scope      the context: scope.files, scope.read_text(), scope.line_count(), …
    file       opt-in PER-FILE mode: henxels runs your function once per file in scope
    root       the repo root (Path)
    settings   the contract's settings dict
    diff       the staged diff (StagedDiff) at commit time, else None — for rules about
               *change*: diff.modified/added/deleted, diff.old_text()/new_text()

Return convention (any of these):

    True / None        pass
    a string           FAIL, and the string is the instruction shown to the agent
    a list of strings  FAIL, multiple instructions
    False              FAIL, falling back to the henxel's own sentence as the instruction

Examples:

    @statement("max_lines")                 # per-file: just describe one file
    def max_lines(param, file, scope):
        if scope.line_count(file) > param:
            return f"split {file}: keep it under {param} lines"

    @statement("has_readme")                # whole-scope: return instruction(s)
    def has_readme(scope):
        return None if scope.exists("README.md") else "add a README.md at the root"
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass

STAGES = ("pre_commit", "pre_push")
INJECTABLE = ("param", "scope", "file", "root", "settings", "diff")


@dataclass
class StatementDef:
    name: str
    fn: Callable
    stage: str | None = None
    params: tuple[str, ...] = ()
    per_file: bool = False  # True when the function asks for `file`
    help: str = ""  # one-line description, shown by `henxels statements`
    builtin: bool = False  # built-ins ship with henxels; others are custom


_REGISTRY: dict[str, StatementDef] = {}


def statement(name: str, *, stage: str | None = None, help: str | None = None, builtin: bool = False):
    """Register a verification function under ``name`` (arguments injected by name)."""
    if stage is not None and stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}; use one of {STAGES}")

    def decorate(fn: Callable) -> Callable:
        params = tuple(inspect.signature(fn).parameters)
        unknown = [p for p in params if p not in INJECTABLE]
        if unknown:
            raise TypeError(
                f"statement '{name}' has unknown parameter(s) {unknown}; "
                f"choose from {INJECTABLE}"
            )
        summary = help or (inspect.getdoc(fn) or "").split("\n", 1)[0]
        _REGISTRY[name] = StatementDef(
            name=name, fn=fn, stage=stage, params=params,
            per_file="file" in params, help=summary, builtin=builtin,
        )
        return fn

    return decorate


def get_statement(name: str) -> StatementDef | None:
    return _REGISTRY.get(name)


def all_statements() -> dict[str, StatementDef]:
    return dict(_REGISTRY)


def as_list(value):
    """Accept a scalar in place of a one-item list (used by every multi-arg statement)."""
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple)) else [value]
