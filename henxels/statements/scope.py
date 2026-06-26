"""The context handed to every statement function.

The model's ceiling is the context's reach, so Scope is deliberately generous: the
files in scope, the whole repo, file contents, line counts, folder listings, and
existence — plus naming helpers. Diff/history accessors are layered on in the hook
runner. A statement uses whatever it needs and ignores the rest.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from henxels.casing import NAMING_CONVENTIONS, is_dunder
from henxels.engine.discover import DEFAULT_EXCLUDES


@dataclass
class Scope:
    root: Path
    locations: list[str]  # normalized; "" means the repo root
    files: list[str]  # repo-relative files under any location
    all_files: list[str] = field(default_factory=list)
    settings: dict = field(default_factory=dict)

    # --- content ---------------------------------------------------------
    def read_text(self, rel: str) -> str | None:
        p = self.root / rel
        try:
            return p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    def line_count(self, rel: str) -> int:
        text = self.read_text(rel)
        return 0 if text is None else text.count("\n") + (0 if text.endswith("\n") or not text else 1)

    # --- existence / folders --------------------------------------------
    def exists(self, rel: str) -> bool:
        return (self.root / rel).exists()

    def is_dir(self, rel: str) -> bool:
        return (self.root / rel).is_dir()

    def subfolders_of(self, location: str) -> list[str]:
        base = self.root / location if location else self.root
        if not base.is_dir():
            return []
        out = []
        for entry in os.scandir(base):
            if entry.is_dir() and entry.name not in DEFAULT_EXCLUDES and not entry.name.startswith("."):
                out.append(entry.name)
        return sorted(out)

    # --- naming helpers (handy for custom statements) -------------------
    @staticmethod
    def base_name(rel: str) -> str:
        return rel.rsplit("/", 1)[-1].split(".")[0]

    def matches_casing(self, rel: str, convention: str) -> bool:
        pattern = NAMING_CONVENTIONS.get(convention)
        if pattern is None:
            return True
        base = self.base_name(rel)
        return not base or is_dunder(base) or bool(re.match(pattern, base))

    def is_kebab(self, rel: str) -> bool:
        return self.matches_casing(rel, "kebab-case")


def build_scope(locations, all_files, root, settings) -> Scope:
    from henxels.locations import parse_all

    locs = parse_all(locations)
    bases = list(dict.fromkeys(loc.base for loc in locs))  # for existence/folder statements
    files = [f for f in all_files if any(loc.matches(f) for loc in locs)]
    return Scope(root=Path(root), locations=bases, files=files, all_files=list(all_files), settings=settings or {})
