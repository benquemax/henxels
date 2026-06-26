"""Shared helpers for the built-in statements."""

from __future__ import annotations

import yaml

from henxels.util.glob import glob_match


def file_matches(pattern: str, path: str) -> bool:
    """Match a file by extension (``.md``) or glob (``*.md`` / ``a/*.py``)."""
    name = path.rsplit("/", 1)[-1]
    if pattern.startswith(".") and "*" not in pattern and "?" not in pattern:
        return name.endswith(pattern)  # ".md" means extension
    return glob_match(pattern, name) or glob_match(pattern, path)


def bare_name(pattern: str, name: str) -> bool:
    """A wildcard-free pattern matches a basename anywhere in the tree."""
    if "/" in pattern or "*" in pattern or "?" in pattern:
        return False
    return name == pattern


def parse_frontmatter(text: str | None) -> dict:
    """Parse a leading ``---`` YAML frontmatter block into a dict (empty if none)."""
    if not text or not text.startswith("---"):
        return {}
    lines = text.splitlines()
    end = next((i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)
    if end is None:
        return {}
    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}
