"""`henxels explain <path>` — the closest-rule-in-tree contract for a location.

This is the steering keystone: before creating or moving a file, an agent (or human)
asks "what governs this spot, and where does this kind of thing actually go?" and
gets a plain-language answer drawn straight from the contract.
"""

from __future__ import annotations

from henxels.config.load import Config
from henxels.config.tree import resolve


def explain_path(config: Config, rel_path: str) -> str:
    """Return a plain-language description of the henxels governing ``rel_path``."""
    r = resolve(config.tree, rel_path)
    lines: list[str] = [f"henxels for {r.path}"]
    lines.append(f"  folder: {r.node_path or '<repo root>'}")

    if r.matched_forbid is not None:
        fb = r.matched_forbid
        lines.append("  ✗ this path is FORBIDDEN here")
        if fb.reason:
            lines.append(f"      why: {fb.reason}")
        if fb.steer:
            lines.append(f"      → {fb.steer}")

    if r.naming:
        lines.append(f"  naming: files here are {r.naming}")

    active_forbid = [f for f in r.forbid if f is not r.matched_forbid]
    if active_forbid:
        lines.append("  forbidden here:")
        for fb in active_forbid:
            tail = f" — {fb.reason}" if fb.reason else ""
            lines.append(f"    - {fb.glob}{tail}")

    if r.require:
        lines.append("  this folder must contain:")
        for entry in r.require:
            spec = entry if isinstance(entry, dict) else {"file": entry}
            tail = f" — {spec['reason']}" if spec.get("reason") else ""
            lines.append(f"    - {spec.get('file', '?')}{tail}")

    if r.mirror:
        lines.append(f"  mirrors: {r.mirror}")

    if len(lines) == 2:  # only path + folder, nothing governs it
        lines.append("  (no henxels apply here — the contract is silent)")

    return "\n".join(lines)
