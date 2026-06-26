"""Existence henxel: a file (or folder) must be present.

Two flavours:

* **Folder-level** (`require` under a tree node): "if this folder exists, it must
  contain handlers.py."
* **Root-level** (top-level `require`): "this repo must have `_todo.md` and
  `_temp/.gitkeep`" — handy for gitignored-but-mandatory scaffolding.

Existence is checked against the **filesystem**, so a gitignored file that's present
locally still satisfies the henxel. Each entry may set ``severity: warn`` to remind
without blocking (e.g. a gitignored file that won't exist in a fresh CI checkout).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from henxels.config.tree import RULE_KEYS
from henxels.findings import BLOCK, WARN, Finding


def check_required(tree: dict, root: Path | str) -> list[Finding]:
    """Folder-level ``require`` henxels across the contract tree."""
    root = Path(root)
    findings: list[Finding] = []
    for node_path, node in _walk(tree):
        require = node.get("require")
        if not require:
            continue
        folder = root / node_path if node_path else root
        if not folder.is_dir():
            continue  # "if the folder exists…" — don't force the folder itself here
        for entry in _as_list(require):
            finding = _check_entry(entry, base=node_path, root=root)
            if finding:
                findings.append(finding)
    return findings


def check_root_required(require: list, root: Path | str) -> list[Finding]:
    """Top-level ``require`` henxels — repo-root files/folders that must exist."""
    root = Path(root)
    findings: list[Finding] = []
    for entry in _as_list(require):
        finding = _check_entry(entry, base="", root=root)
        if finding:
            findings.append(finding)
    return findings


def _check_entry(entry, base: str, root: Path) -> Finding | None:
    spec = entry if isinstance(entry, dict) else {"file": entry}
    filename = spec.get("file")
    if not filename:
        return None
    rel = f"{base}/{filename}" if base else filename
    if (root / rel).exists():  # exists() so a required folder (via .gitkeep path) works
        return None
    level = WARN if str(spec.get("severity", "")).lower() == "warn" else BLOCK
    where = base or "the repo root"
    return Finding(
        level=level,
        henxel="require",
        path=rel,
        message=f"required path is missing from {where}",
        reason=spec.get("reason"),
        steer=f"create {rel}",
        fix="or drop this `require` from henxels.yaml",
    )


def _walk(tree: dict, prefix: str = "") -> Iterator[tuple[str, dict]]:
    if not isinstance(tree, dict):
        return
    for key, value in tree.items():
        if key in RULE_KEYS or not isinstance(value, dict):
            continue
        node_path = f"{prefix}/{key}" if prefix else key
        yield node_path, value
        yield from _walk(value, node_path)


def _as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]
