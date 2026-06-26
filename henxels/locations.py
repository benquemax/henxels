"""Parse a henxel's ``in:`` scope into something we can match files against.

Paths are anchored at the repo root (``./`` recommended). Recursion is **explicit**
via a trailing asterisk:

    ./docs          files directly in docs/        (this level only)
    ./docs/*        docs/ and all subfolders        (recursive)
    ./              files directly at the repo root
    ./*             the whole repo                  (recursive)
    ./docs/intro.md a specific file
    ./docs/*.md     a glob (md files in docs)

No ``in:`` defaults to ``./*`` so repo-wide rules still catch everything.
"""

from __future__ import annotations

from dataclasses import dataclass

from henxels.util.glob import glob_match

DEFAULT_SCOPE = "./*"


@dataclass
class Location:
    raw: str
    base: str  # the folder for existence/folder statements ("" = repo root)
    kind: str  # "folder" | "file" | "glob"
    recursive: bool = False
    target: str = ""  # for kind == "file"
    pattern: str = ""  # for kind == "glob"

    def matches(self, path: str) -> bool:
        """True if a file ``path`` falls within this scope."""
        path = path.replace("\\", "/")
        if self.kind == "file":
            return path == self.target
        if self.kind == "glob":
            return glob_match(self.pattern, path)
        # folder
        if self.recursive:
            return self.base == "" or path == self.base or path.startswith(self.base + "/")
        return _dirname(path) == self.base

    def governs(self, path: str) -> bool:
        """Looser than matches(): used by `explain` so a folder henxel shows for the
        folder and its descendants, even when its file checks are non-recursive."""
        path = path.replace("\\", "/").strip("/")
        if self.matches(path):
            return True
        if self.kind == "folder":
            if self.base == "":
                return self.recursive
            return path == self.base or path.startswith(self.base + "/")
        return False


def parse(spec: str) -> Location:
    raw = spec
    s = str(spec).strip()
    if s.startswith("./"):
        s = s[2:]
    elif s == ".":
        s = ""

    recursive = False
    if s.endswith("/**"):
        recursive, s = True, s[:-3]
    elif s.endswith("/*"):
        recursive, s = True, s[:-2]
    elif s == "*":
        recursive, s = True, ""

    s = s.strip("/")

    if recursive:
        return Location(raw=raw, base=s, kind="folder", recursive=True)
    if "*" in s or "?" in s:
        base = s.rsplit("/", 1)[0] if "/" in s else ""
        return Location(raw=raw, base=base, kind="glob", pattern=s)
    if s == "":
        return Location(raw=raw, base="", kind="folder")
    if "." in s.rsplit("/", 1)[-1]:
        base = s.rsplit("/", 1)[0] if "/" in s else ""
        return Location(raw=raw, base=base, kind="file", target=s)
    return Location(raw=raw, base=s, kind="folder")


def parse_all(specs) -> list[Location]:
    specs = specs if isinstance(specs, list) else [specs]
    return [parse(s) for s in (specs or [DEFAULT_SCOPE])]


def _dirname(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""
