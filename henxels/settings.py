"""Read behaviours from the contract's ``settings:`` block.

Settings are the things that aren't tests: protections that intercept a git action,
and tuning knobs. Each accessor normalizes the loose YAML (bool or mapping) into a
predictable value.
"""

from __future__ import annotations

from henxels.contract import Contract

DEFAULT_DELETE_LINES = 5
DEFAULT_SIMILARITY = 0.85
DEFAULT_AT_MOST = 20  # duplicate warnings shown before we switch to a count
DEFAULT_LARGE_FILE = "8000 tokens"


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
    """Return {'above', 'ignore', 'at_most', 'budget'} when similarity warnings are on."""
    raw = contract.settings.get("warn_about_similar_files")
    if not raw:
        return None
    if raw is True:
        return {"above": DEFAULT_SIMILARITY, "ignore": [], "at_most": DEFAULT_AT_MOST, "budget": None}
    if isinstance(raw, dict):
        return {
            "above": float(raw.get("above", DEFAULT_SIMILARITY)),
            "ignore": raw.get("ignore", []) or [],
            "at_most": int(raw.get("at_most", DEFAULT_AT_MOST)),
            "budget": _budget_seconds(raw.get("budget")),
        }
    return None


def _budget_seconds(raw) -> float | None:
    """``budget`` is seconds: a number, or a string with an s/m/h suffix ("30s", "5m")."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip().lower()
    units = {"s": 1.0, "m": 60.0, "h": 3600.0}
    if text and text[-1] in units:
        return float(text[:-1]) * units[text[-1]]
    return float(text)


def large_files(contract: Contract) -> dict | None:
    """Return {'over': '<n> <unit>', 'ignore': [...]} when large-file warnings are on."""
    raw = contract.settings.get("warn_about_large_files")
    if not raw:
        return None
    if raw is True:
        return {"over": DEFAULT_LARGE_FILE, "ignore": []}
    if isinstance(raw, dict):
        return {"over": str(raw.get("over", DEFAULT_LARGE_FILE)), "ignore": raw.get("ignore", []) or []}
    return None
