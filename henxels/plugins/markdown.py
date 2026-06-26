"""Markdown plugin: lint .md files via pymarkdownlnt (optional dependency).

Enabled with ``plugins: { markdown: true }``. Findings are warnings — formatting is
advisory, not structural. If pymarkdownlnt isn't installed we degrade to silence;
`henxels doctor` is the place to notice it's missing.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from henxels.config.load import Config
from henxels.findings import WARN, Finding


def check_markdown(config: Config, root: Path | str, rel_paths: list[str]) -> list[Finding]:
    if not config.plugins.get("markdown"):
        return []
    cmd = _pymarkdown_cmd()
    if cmd is None:
        return []  # optional dep absent — silently skip (doctor can report)

    root = Path(root)
    findings: list[Finding] = []
    for rel in rel_paths:
        if not rel.endswith(".md"):
            continue
        result = subprocess.run(
            [*cmd, "scan", str(root / rel)], capture_output=True, text=True
        )
        if result.returncode == 0:
            continue
        for line in result.stdout.splitlines():
            parsed = _parse_line(line, rel)
            if parsed:
                findings.append(parsed)
    return findings


def _pymarkdown_cmd() -> list[str] | None:
    venv_bin = Path(sys.executable).parent / "pymarkdown"
    if venv_bin.exists():
        return [str(venv_bin)]
    found = shutil.which("pymarkdown")
    return [found] if found else None


def _parse_line(line: str, rel: str) -> Finding | None:
    # pymarkdown format: path:line:col: MDxxx: message
    parts = line.split(":", 4)
    if len(parts) < 5:
        return None
    return Finding(
        level=WARN,
        henxel="markdown",
        path=rel,
        message=f"{parts[3].strip()}: {parts[4].strip()} (line {parts[1]})",
        reason="markdown formatting (plugins.markdown)",
        steer="fix the formatting or disable plugins.markdown",
    )
