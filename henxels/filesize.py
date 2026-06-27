"""Large-file awareness — warn (never block) when a file gets heavy for an agent.

Tokens are the agent-native unit (a file is read into a context window measured in
tokens), so the threshold is unit-aware: ``8000 tokens`` / ``200 lines`` / ``3 kb``.
Token counts are a dependency-free estimate (``chars / 4``) and are always labelled
``(estimated)`` — henxels doesn't ship a tokenizer.
"""

from __future__ import annotations

import re
from pathlib import Path

from henxels.findings import WARN, Finding
from henxels.util.glob import glob_match

# <number> + optional space + unit (unit REQUIRED — a bare number is rejected).
_THRESHOLD_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(b|kb|mb|gb|tokens|lines)\s*$", re.IGNORECASE)
_MULT = {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3}


def parse_threshold(spec) -> tuple[float, str] | None:
    """``"8000 tokens"`` → ``(8000.0, "tokens")``. None if no valid unit is given."""
    match = _THRESHOLD_RE.match(str(spec))
    if not match:
        return None
    return float(match.group(1)), match.group(2).lower()


def warn_large_files(cfg: dict | None, root: Path | str, candidates: list[str]) -> list[Finding]:
    """Settings-driven large-file warnings. ``cfg`` = {'over', 'ignore'} or None."""
    if not cfg:
        return []
    parsed = parse_threshold(cfg.get("over"))
    if not parsed:
        return []  # invalid/missing unit → no-op rather than nag
    amount, unit = parsed
    excludes = cfg.get("ignore", []) or []
    root = Path(root)

    findings: list[Finding] = []
    for rel in candidates:
        if any(glob_match(p, rel) for p in excludes):
            continue
        measure = _measure(root, rel, unit)
        if measure is None:
            continue
        if measure > amount * _MULT.get(unit, 1):
            findings.append(
                Finding(level=WARN, henxel=f"Large file: {rel}", path=rel, message="", details=[_detail(measure, amount, unit)])
            )
    return findings


def _measure(root: Path, rel: str, unit: str) -> float | None:
    path = root / rel
    if unit in _MULT:  # byte units measure any file
        try:
            return float(path.stat().st_size)
        except OSError:
            return None
    text = _read_text(path)  # lines/tokens need text
    if text is None:
        return None
    if unit == "lines":
        return float(text.count("\n") + (1 if text and not text.endswith("\n") else 0))
    return len(text) / 4  # tokens — estimate


def _detail(measure: float, amount: float, unit: str) -> str:
    if unit == "tokens":
        return f"~{int(measure)} tokens (estimated) — over the {int(amount)}-token budget; consider splitting"
    if unit == "lines":
        return f"{int(measure)} lines — over the {int(amount)}-line budget; consider splitting"
    return f"{_human_bytes(measure)} — over the {int(amount)} {unit} budget; consider splitting"


def _human_bytes(n: float) -> str:
    if n < 1024:
        return f"{int(n)} b"
    if n < 1024**2:
        return f"{n / 1024:.1f} kb"
    if n < 1024**3:
        return f"{n / 1024**2:.1f} mb"
    return f"{n / 1024**3:.1f} gb"


def _read_text(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data:  # binary
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None
