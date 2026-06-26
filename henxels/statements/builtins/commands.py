"""Command-gate statements: a command that must pass at a git stage.

These are skipped during ``henxels check`` and executed by the git hooks.
"""

from __future__ import annotations

from henxels.statements.registry import statement


@statement("run_before_commit", stage="pre_commit", help="command that must pass before a commit", builtin=True)
def run_before_commit(param, scope):  # pragma: no cover - executed by hooks
    return []


@statement("run_before_push", stage="pre_push", help="command that must pass before a push", builtin=True)
def run_before_push(param, scope):  # pragma: no cover - executed by hooks
    return []
