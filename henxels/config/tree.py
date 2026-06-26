"""Closest-rule-in-tree resolution.

The contract's ``tree:`` mirrors the repo's folders. For any path we walk from the
root down to the file's directory, collecting the henxels that apply:

* ``naming``  — scalar; the *closest* ancestor that sets it wins (cascades down).
* ``forbid``  — list; *accumulates* from every ancestor (each glob is evaluated
                relative to the node that declared it, so a forbid at ``src`` covers
                everything beneath ``src``).
* ``require`` — belongs to a folder node itself (does this folder contain X?).
* ``mirror``  — belongs to a folder node itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from henxels.util.glob import glob_match

# Keys at a tree node that are rules rather than child folders.
RULE_KEYS = frozenset({"naming", "forbid", "require", "mirror", "purpose"})


@dataclass
class Forbidden:
    """A single ``forbid`` henxel, with the node it was declared at."""

    glob: str
    reason: str | None = None
    steer: str | None = None
    node: str = ""  # node path where this forbid was declared ("" = root)


@dataclass
class Resolved:
    """The henxels that apply to a single path."""

    path: str
    naming: str | None = None
    forbid: list[Forbidden] = field(default_factory=list)
    require: list[Any] = field(default_factory=list)
    mirror: str | None = None
    node_path: str = ""  # deepest folder node matched ("" = repo root)
    matched_forbid: Forbidden | None = None  # first forbid this path actually violates


def resolve(tree: dict, rel_path: str) -> Resolved:
    """Resolve the applicable henxels for ``rel_path`` against ``tree``."""
    norm = str(rel_path).replace("\\", "/")
    parts = [p for p in PurePosixPath(norm).parts if p not in ("", ".")]
    dir_parts = parts[:-1] if parts else []

    res = Resolved(path=norm)
    current = tree if isinstance(tree, dict) else {}
    segs: list[str] = []
    nodes: list[tuple[str, dict]] = []

    for seg in dir_parts:
        nxt = current.get(seg) if isinstance(current, dict) else None
        if isinstance(nxt, dict):
            segs.append(seg)
            nodes.append(("/".join(segs), nxt))
            current = nxt
        else:
            break

    for node_path, ndef in nodes:
        naming = ndef.get("naming")
        if isinstance(naming, str):
            res.naming = naming  # deeper node overrides shallower
        for entry in _as_list(ndef.get("forbid")):
            res.forbid.append(_to_forbidden(entry, node_path))

    if nodes:
        deepest_path, deepest = nodes[-1]
        res.node_path = deepest_path
        res.require = _as_list(deepest.get("require"))
        mirror = deepest.get("mirror")
        if isinstance(mirror, str):
            res.mirror = mirror

    for fb in res.forbid:
        relative = _relative_to(norm, fb.node)
        if relative is not None and glob_match(fb.glob, relative):
            res.matched_forbid = fb
            break

    return res


def _to_forbidden(entry: Any, node_path: str) -> Forbidden:
    if isinstance(entry, str):
        return Forbidden(glob=entry, node=node_path)
    if isinstance(entry, dict):
        return Forbidden(
            glob=entry.get("glob", ""),
            reason=entry.get("reason"),
            steer=entry.get("steer"),
            node=node_path,
        )
    return Forbidden(glob="", node=node_path)


def _relative_to(path: str, node: str) -> str | None:
    """Path relative to a node's folder, or None if ``path`` isn't under ``node``."""
    if not node:
        return path
    prefix = node + "/"
    if path.startswith(prefix):
        return path[len(prefix):]
    if path == node:
        return ""
    return None


def _as_list(value: Any) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]
