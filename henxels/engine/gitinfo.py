"""Thin git plumbing used by check (staged files) and the guards.

Everything here degrades gracefully: if git is missing or this isn't a repo, the
callers fall back to non-git behavior rather than crashing.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def is_git_repo(root: Path | str) -> bool:
    return (Path(root) / ".git").exists()


def _run(args: list[str], root: Path | str) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(args, capture_output=True, text=True, cwd=str(root))
    except FileNotFoundError:
        return None


def staged_files(root: Path | str) -> list[str]:
    """Added/copied/modified files staged for commit (posix relative paths)."""
    res = _run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"], root
    )
    if res is None or res.returncode != 0:
        return []
    return [line for line in res.stdout.splitlines() if line]


def staged_deletions(root: Path | str) -> list[str]:
    """Files deleted in the staged set."""
    res = _run(["git", "diff", "--cached", "--name-only", "--diff-filter=D"], root)
    if res is None or res.returncode != 0:
        return []
    return [line for line in res.stdout.splitlines() if line]


def staged_numstat(root: Path | str) -> list[tuple[int, int, str]]:
    """(added, removed, path) per staged file; binary files report 0/0."""
    res = _run(["git", "diff", "--cached", "--numstat"], root)
    out: list[tuple[int, int, str]] = []
    if res is None or res.returncode != 0:
        return out
    for line in res.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added = 0 if parts[0] == "-" else int(parts[0])
        removed = 0 if parts[1] == "-" else int(parts[1])
        out.append((added, removed, parts[2]))
    return out


def staged_name_status(root: Path | str) -> list[tuple[str, str]]:
    """(status letter, path) per staged change: A/M/D (renames reported as M on the new path)."""
    res = _run(["git", "diff", "--cached", "--name-status"], root)
    out: list[tuple[str, str]] = []
    if res is None or res.returncode != 0:
        return out
    for line in res.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            out.append((parts[0][0], parts[-1]))  # parts[-1] = new path (handles R<score>\told\tnew)
    return out


def file_at_head(root: Path | str, rel: str) -> str | None:
    """Contents of ``rel`` at HEAD (None if absent or not a repo)."""
    res = _run(["git", "show", f"HEAD:{rel}"], root)
    return res.stdout if res is not None and res.returncode == 0 else None


def file_in_index(root: Path | str, rel: str) -> str | None:
    """Staged contents of ``rel`` (the version that would be committed)."""
    res = _run(["git", "show", f":{rel}"], root)
    return res.stdout if res is not None and res.returncode == 0 else None


def tracked_files(root: Path | str) -> list[str]:
    """Files committed/tracked by git (the corpus similarity compares against)."""
    res = _run(["git", "ls-files"], root)
    if res is None or res.returncode != 0:
        return []
    return [line for line in res.stdout.splitlines() if line]


def head_sha(root: Path | str) -> str | None:
    res = _run(["git", "rev-parse", "HEAD"], root)
    if res is None or res.returncode != 0:
        return None
    return res.stdout.strip() or None
