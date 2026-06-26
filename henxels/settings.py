"""Read behaviours from the contract's ``settings:`` block.

Settings are the things that aren't tests: protections that intercept a git action,
and tuning knobs. Each accessor normalizes the loose YAML (bool or mapping) into a
predictable value.
"""

from __future__ import annotations

from henxels.contract import Contract

DEFAULT_DELETE_LINES = 5
DEFAULT_SIMILARITY = 0.85


def ask_me_before_staging(contract: Contract) -> bool:
    return bool(contract.settings.get("ask_me_before_staging"))


def confirm_before_push(contract: Contract) -> bool:
    return bool(contract.settings.get("confirm_before_push"))


def delete_protection(contract: Contract) -> dict | None:
    """Return {'over_lines': N} when the delete protection is on, else None."""
    raw = contract.settings.get("confirm_before_deleting")
    if not raw:
        return None
    if raw is True:
        return {"over_lines": DEFAULT_DELETE_LINES}
    if isinstance(raw, dict):
        return {"over_lines": int(raw.get("over_lines", DEFAULT_DELETE_LINES))}
    return None


def similarity(contract: Contract) -> dict | None:
    """Return {'above': float, 'ignore': [...]} when similarity warnings are on."""
    raw = contract.settings.get("warn_about_similar_files")
    if not raw:
        return None
    if raw is True:
        return {"above": DEFAULT_SIMILARITY, "ignore": []}
    if isinstance(raw, dict):
        return {
            "above": float(raw.get("above", DEFAULT_SIMILARITY)),
            "ignore": raw.get("ignore", []) or [],
        }
    return None
