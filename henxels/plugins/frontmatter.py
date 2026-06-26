"""Frontmatter plugin: require YAML frontmatter keys on markdown files in a folder.

Dependency-free — we parse the leading ``---`` block with the YAML we already depend
on. Enabled per top-level folder:

    plugins:
      frontmatter:
        docs: [title, date]
"""

from __future__ import annotations

from pathlib import Path

import yaml

from henxels.config.load import Config
from henxels.findings import BLOCK, Finding


def check_frontmatter(config: Config, root: Path | str, rel_paths: list[str]) -> list[Finding]:
    spec = config.plugins.get("frontmatter")
    if not isinstance(spec, dict):
        return []
    root = Path(root)
    findings: list[Finding] = []
    for rel in rel_paths:
        if not rel.endswith(".md"):
            continue
        top = rel.split("/")[0]
        required = spec.get(top)
        if not required:
            continue
        meta = _parse_frontmatter(root / rel)
        for key in required:
            if key not in meta:
                findings.append(
                    Finding(
                        level=BLOCK,
                        henxel="frontmatter",
                        path=rel,
                        message=f"missing frontmatter key '{key}'",
                        reason=f"{top}/ markdown must declare `{key}`",
                        steer=f"add `{key}:` to the frontmatter block",
                        fix="or relax plugins.frontmatter in henxels.yaml",
                    )
                )
    return findings


def _parse_frontmatter(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return {}
    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}
