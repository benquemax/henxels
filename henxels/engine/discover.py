"""Find the files a contract should govern.

Prefers git (so ``.gitignore`` is honored automatically); falls back to a plain
filesystem walk with sensible excludes when git isn't available.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# Always skipped, git or not — noise that no contract cares about.
DEFAULT_EXCLUDES = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "ENV",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".tox",
        "dist",
        "build",
        ".idea",
        ".vscode",
        "_temp",
        ".eggs",
    }
)


def discover(root: Path | str, excludes: set[str] | None = None, use_git: bool = True) -> list[str]:
    """Return repo-relative posix paths of files to govern, sorted."""
    root = Path(root)
    skip = set(DEFAULT_EXCLUDES) | set(excludes or ())

    paths: list[str] | None = None
    if use_git and (root / ".git").exists():
        paths = _git_files(root)

    if paths is None:
        paths = _walk_files(root)

    return sorted(p for p in paths if not _excluded(p, skip))


def _excluded(rel: str, skip: set[str]) -> bool:
    return any(part in skip for part in rel.split("/"))


def _git_files(root: Path) -> list[str] | None:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            cwd=root,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    return [line for line in result.stdout.splitlines() if line]


def _walk_files(root: Path) -> list[str]:
    out: list[str] = []
    for p in root.rglob("*"):
        if p.is_file():
            out.append(p.relative_to(root).as_posix())
    return out
