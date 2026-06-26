"""Content statements: what's inside the files (frontmatter, markdown quality)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from henxels.statements.builtins._helpers import parse_frontmatter
from henxels.statements.registry import as_list, statement


@statement("required_frontmatter", help="markdown files declare these frontmatter keys (list = all)", builtin=True)
def required_frontmatter(param, scope):
    keys = as_list(param)
    violations = []
    for f in scope.files:
        if not f.endswith(".md"):
            continue
        meta = parse_frontmatter(scope.read_text(f))
        for key in keys:
            if key not in meta:
                violations.append(f"{f} — add frontmatter key '{key}'")
    return violations


@statement("markdown_lint", help="markdown files pass pymarkdownlnt (pip install pymarkdownlnt)", builtin=True)
def markdown_lint(scope):
    md_files = [f for f in scope.files if f.endswith(".md")]
    if not md_files:
        return []
    cmd = _pymarkdown_cmd()
    if cmd is None:
        return ["install pymarkdownlnt to enable markdown_lint:  pip install pymarkdownlnt"]

    issues = []
    for f in md_files:
        # Enable front-matter parsing (so YAML `---` isn't read as a setext heading);
        # rule toggles come from the repo's pymarkdown config ([tool.pymarkdown]).
        result = subprocess.run(
            [*cmd, "--set", "extensions.front-matter.enabled=$!True", "scan", str(scope.root / f)],
            capture_output=True,
            text=True,
            cwd=str(scope.root),
        )
        if result.returncode == 0:
            continue
        for line in result.stdout.splitlines():
            parts = line.split(":", 4)
            if len(parts) >= 5:
                issues.append(f"{f} — {parts[3].strip()}: {parts[4].strip()} (line {parts[1]})")
    return issues


def _pymarkdown_cmd():
    venv_bin = Path(sys.executable).parent / "pymarkdown"
    if venv_bin.exists():
        return [str(venv_bin)]
    found = shutil.which("pymarkdown")
    return [found] if found else None
