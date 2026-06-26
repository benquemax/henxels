"""Naming statements: how files in scope are named.

Both are MATCH statements — a list means "any of these is acceptable" (OR).
"""

from __future__ import annotations

import re

from henxels.casing import NAMING_CONVENTIONS
from henxels.statements.registry import as_list, statement


@statement("filename_casing", help="file names use this naming convention (snake_case, kebab-case, …)", builtin=True)
def filename_casing(param, scope):
    conventions = as_list(param)
    unknown = [c for c in conventions if c not in NAMING_CONVENTIONS]
    if unknown:
        return [f"unknown casing {unknown[0]!r} (use {', '.join(NAMING_CONVENTIONS)})"]
    violations = []
    for f in scope.files:
        if not any(scope.matches_casing(f, c) for c in conventions):
            violations.append(f"{f} — rename to {' or '.join(conventions)}")
    return violations


@statement("filename_matches_regex", help="every file name matches a regex (list = any of)", builtin=True)
def filename_matches_regex(param, scope):
    regexes = [re.compile(p) for p in as_list(param)]
    violations = []
    for f in scope.files:
        name = f.rsplit("/", 1)[-1]
        if not any(rx.search(name) for rx in regexes):
            violations.append(f"{f} — name must match the required pattern")
    return violations
