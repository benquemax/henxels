"""Placement henxel: ``forbid`` a kind of file from living in a folder subtree.

This is the core "right stuff, right place" steer. The resolver already figured out
whether the path violates a forbid; we just turn that into a teaching finding.
"""

from __future__ import annotations

from henxels.config.tree import Resolved
from henxels.findings import BLOCK, Finding


def check_placement(resolved: Resolved) -> list[Finding]:
    fb = resolved.matched_forbid
    if fb is None:
        return []

    where = fb.node or "the repo root"
    return [
        Finding(
            level=BLOCK,
            henxel="placement",
            path=resolved.path,
            message=f"forbidden under {where} (matches '{fb.glob}')",
            reason=fb.reason,
            steer=fb.steer,
            fix="if this truly belongs here, relax the `forbid` in henxels.yaml",
        )
    ]
