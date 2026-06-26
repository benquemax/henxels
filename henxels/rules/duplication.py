"""Canonical single-source henxel: a thing has exactly one home.

Each ``canonical`` entry names the one file a role lives in, and optionally forbids
look-alikes — files that would duplicate that role (a second config, a stray
``setup.py`` beside ``pyproject.toml``). Look-alikes block; the steer points at the
real home.
"""

from __future__ import annotations

from henxels.config.load import Config
from henxels.findings import BLOCK, Finding
from henxels.util.glob import glob_match


def check_canonical(config: Config, files: list[str]) -> list[Finding]:
    """Flag any file that duplicates a canonical role."""
    findings: list[Finding] = []
    for entry in config.canonical:
        if not isinstance(entry, dict):
            continue
        home = entry.get("file")
        role = entry.get("role") or (f"the role of {home}" if home else "this role")
        lookalikes = entry.get("forbid_lookalikes") or []
        for f in files:
            if f == home:
                continue
            if any(glob_match(pattern, f) or _basename_match(pattern, f) for pattern in lookalikes):
                findings.append(
                    Finding(
                        level=BLOCK,
                        henxel="canonical",
                        path=f,
                        message=f"duplicates {role} (which lives in {home})",
                        reason="one source of truth; a second copy invites divergence",
                        steer=f"put it in {home} instead of {f}",
                        fix="or change the `canonical` henxel in henxels.yaml",
                    )
                )
    return findings


def _basename_match(pattern: str, path: str) -> bool:
    """Allow bare filenames in forbid_lookalikes to match anywhere in the tree."""
    if "/" in pattern or "*" in pattern or "?" in pattern:
        return False
    return path.rsplit("/", 1)[-1] == pattern
