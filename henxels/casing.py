"""Naming conventions — the closed set used by the `casing` statement and Scope."""

from __future__ import annotations

import re

# Keys are the values accepted by the `casing:` statement (and the schema enum).
# snake_case / SCREAMING_SNAKE_CASE permit leading underscores — `_private.py` and
# `_helpers.py` are idiomatic Python, not naming violations. (Dunder files like
# __init__.py are exempted separately, in is_dunder.)
NAMING_CONVENTIONS: dict[str, str] = {
    "snake_case": r"^_*[a-z0-9]+(_[a-z0-9]+)*$",
    "kebab-case": r"^[a-z0-9]+(-[a-z0-9]+)*$",
    "camelCase": r"^[a-z][a-zA-Z0-9]*$",
    "PascalCase": r"^[A-Z][a-zA-Z0-9]*$",
    "SCREAMING_SNAKE_CASE": r"^_*[A-Z0-9]+(_[A-Z0-9]+)*$",
    "any": r".*",
}


def is_dunder(base: str) -> bool:
    """Dunder files (__init__, __main__) are language-mandated, not style choices."""
    return len(base) > 4 and base.startswith("__") and base.endswith("__")


def matches(base: str, convention: str) -> bool:
    pattern = NAMING_CONVENTIONS.get(convention)
    if pattern is None:
        return True
    return not base or is_dunder(base) or bool(re.match(pattern, base))
