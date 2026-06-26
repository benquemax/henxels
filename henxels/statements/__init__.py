"""Statements: the extensible verification vocabulary.

Importing this package registers all built-in statements.
"""

# Importing builtins registers the built-in statements as a side effect.
from henxels.statements import builtins  # noqa: E402,F401
from henxels.statements.registry import (
    StatementDef,
    all_statements,
    as_list,
    get_statement,
    statement,
)
from henxels.statements.scope import Scope, build_scope

__all__ = [
    "StatementDef",
    "all_statements",
    "as_list",
    "get_statement",
    "statement",
    "Scope",
    "build_scope",
]
