"""Naming henxel: a folder can require a naming convention for the files in it.

We validate the *base name* up to the first dot (so ``button.test.tsx`` is judged on
``button``), which keeps multi-extension files friendly.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from henxels.config.tree import Resolved
from henxels.findings import BLOCK, Finding

# The closed set of naming conventions. The JSON Schema enum is generated from these
# keys, so editors and the validator never disagree.
NAMING_CONVENTIONS: dict[str, str] = {
    "snake_case": r"^[a-z0-9]+(_[a-z0-9]+)*$",
    "kebab-case": r"^[a-z0-9]+(-[a-z0-9]+)*$",
    "camelCase": r"^[a-z][a-zA-Z0-9]*$",
    "PascalCase": r"^[A-Z][a-zA-Z0-9]*$",
    "SCREAMING_SNAKE_CASE": r"^[A-Z0-9]+(_[A-Z0-9]+)*$",
    "any": r".*",
}


def check_naming(resolved: Resolved) -> list[Finding]:
    """Check the file's base name against the closest naming henxel."""
    convention = resolved.naming
    if not convention or convention == "any":
        return []

    pattern = NAMING_CONVENTIONS.get(convention)
    if pattern is None:
        # Unknown convention name in the contract — treat as a (blocking) mistake.
        return [
            Finding(
                level=BLOCK,
                henxel="naming",
                path=resolved.path,
                message=f"unknown naming convention '{convention}'",
                steer=f"use one of: {', '.join(NAMING_CONVENTIONS)}",
                fix="fix the `naming:` value in henxels.yaml",
            )
        ]

    base = PurePosixPath(resolved.path).name.split(".")[0]
    # Dunder files (__init__, __main__) are language-mandated names, not style choices.
    if _is_dunder(base):
        return []
    if not base or re.match(pattern, base):
        return []

    return [
        Finding(
            level=BLOCK,
            henxel="naming",
            path=resolved.path,
            message=f"name '{base}' is not {convention}",
            reason=f"{resolved.node_path or 'this folder'} uses {convention}",
            steer=f"rename to {convention} (e.g. {_suggest(base, convention)})",
            fix="or change the `naming:` henxel in henxels.yaml",
        )
    ]


def _is_dunder(base: str) -> bool:
    return len(base) > 4 and base.startswith("__") and base.endswith("__")


def _suggest(name: str, convention: str) -> str:
    words = re.split(r"[\s_\-]+|(?<=[a-z0-9])(?=[A-Z])", name)
    words = [w for w in words if w]
    lower = [w.lower() for w in words]
    if convention == "snake_case":
        return "_".join(lower)
    if convention == "kebab-case":
        return "-".join(lower)
    if convention == "SCREAMING_SNAKE_CASE":
        return "_".join(w.upper() for w in lower)
    if convention == "camelCase":
        return lower[0] + "".join(w.capitalize() for w in lower[1:]) if lower else name
    if convention == "PascalCase":
        return "".join(w.capitalize() for w in lower)
    return name
