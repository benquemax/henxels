"""Content statements: what's inside the files (frontmatter, markdown quality)."""

from __future__ import annotations

import datetime
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

from henxels.statements.builtins._helpers import has_frontmatter, parse_frontmatter, split_frontmatter
from henxels.statements.registry import as_list, statement

# [text](target) and ![alt](target) — capture the link/image target.
_MD_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@statement(
    "required_frontmatter",
    help="markdown files declare these frontmatter keys with a non-empty value (list = all)",
    builtin=True,
)
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
            elif _is_empty(meta[key]):
                violations.append(f"{f} — frontmatter key '{key}' is empty; give it a value")
    return violations


def _is_empty(value) -> bool:
    # None, blank strings, and empty collections don't *declare* anything;
    # falsy values like ``false`` and ``0`` do.
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


@statement(
    "frontmatter_dates",
    help="named frontmatter fields are valid ISO dates (YYYY-MM-DD); dict form {field: datetime} allows ISO 8601 datetimes",
    builtin=True,
)
def frontmatter_dates(param, scope):
    # scalar/list = date-only fields; dict = per-field kind ("date" | "datetime")
    expectations = param if isinstance(param, dict) else dict.fromkeys(as_list(param), "date")
    for name, kind in expectations.items():
        if kind not in ("date", "datetime"):
            raise ValueError(f"'{name}: {kind}' — the kind must be 'date' or 'datetime'")
    violations = []
    for f in scope.files:
        if not f.endswith(".md"):
            continue
        meta = parse_frontmatter(scope.read_text(f))
        for name, kind in expectations.items():
            if name not in meta:
                continue  # presence is required_frontmatter's job
            if kind == "date" and not _is_iso_date(meta[name]):
                violations.append(f"{f} — frontmatter '{name}' must be an ISO date (YYYY-MM-DD): {meta[name]!r}")
            elif kind == "datetime" and not _is_iso_datetime(meta[name]):
                violations.append(f"{f} — frontmatter '{name}' must be an ISO 8601 datetime: {meta[name]!r}")
    return violations


@statement(
    "frontmatter_values",
    help="frontmatter fields hold values from an allowed set (scalar ∈ set; list ⊆ set)",
    builtin=True,
)
def frontmatter_values(param, scope):
    spec = param if isinstance(param, dict) else {}
    violations = []
    for f in scope.files:
        if not f.endswith(".md"):
            continue
        meta = parse_frontmatter(scope.read_text(f))
        for name, allowed in spec.items():
            if name not in meta:
                continue  # presence is required_frontmatter's job
            allowed_set = set(as_list(allowed))
            value = meta[name]
            for v in (value if isinstance(value, list) else [value]):
                if v not in allowed_set:
                    violations.append(
                        f"{f} — frontmatter '{name}': {v!r} not allowed (use: {', '.join(map(str, sorted(allowed_set)))})"
                    )
    return violations


@statement(
    "frontmatter_sha256_matches",
    help="frontmatter sha256 field equals the SHA-256 of the body below the frontmatter",
    builtin=True,
)
def frontmatter_sha256_matches(param, scope):
    field = param if isinstance(param, str) else "sha256"
    violations = []
    for f in scope.files:
        if not f.endswith(".md"):
            continue
        meta, body = split_frontmatter(scope.read_text(f))
        if field not in meta:
            continue  # presence is required_frontmatter's job
        declared = str(meta[field]).strip().lower()
        actual = hashlib.sha256(body.encode("utf-8")).hexdigest()
        if declared != actual:
            violations.append(f"{f} — frontmatter '{field}' {declared[:12]}… ≠ body hash {actual[:12]}…; re-hash the body")
    return violations


def _is_iso_date(value) -> bool:
    # An unquoted YAML date becomes a date object (valid by construction); reject datetimes.
    if isinstance(value, datetime.datetime):
        return False
    if isinstance(value, datetime.date):
        return True
    if not isinstance(value, str) or not _ISO_DATE.match(value):
        return False
    try:
        datetime.date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _is_iso_datetime(value) -> bool:
    # Anything YAML already parsed to a date/datetime is valid by construction; a bare
    # date passes too — it's an ISO 8601 instant at day precision.
    if isinstance(value, (datetime.datetime, datetime.date)):
        return True
    if not isinstance(value, str):
        return False
    try:
        # Python 3.10's fromisoformat predates the trailing-Z form.
        datetime.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


@statement(
    "no_frontmatter",
    help="markdown files here carry no YAML frontmatter block (e.g. OKF's reserved index.md/log.md)",
    builtin=True,
)
def no_frontmatter(scope):
    violations = []
    for f in scope.files:
        if not f.endswith(".md"):
            continue
        if has_frontmatter(scope.read_text(f)):
            violations.append(f"{f} — remove the frontmatter block; files here must not carry one")
    return violations


@statement("markdown_lint", help="markdown files pass pymarkdownlnt (pip install pymarkdownlnt)", builtin=True)
def markdown_lint(scope):
    md_files = [f for f in scope.files if f.endswith(".md")]
    if not md_files:
        return []
    cmd = _pymarkdown_cmd()
    if cmd is None:
        # Optional dep absent → don't block a commit over a missing linter.
        # `henxels doctor` surfaces it as a setup nudge instead.
        return []

    # One invocation for the whole set — a subprocess per file costs ~0.3s of
    # interpreter startup each, minutes on a docs-heavy repo. pymarkdown reports
    # per-file `path:line:col:rule:message` lines, so a single scan is enough.
    # Front-matter parsing is enabled (so YAML `---` isn't read as a setext
    # heading); rule toggles come from the repo's pymarkdown config
    # ([tool.pymarkdown]). Relative paths + cwd keep the reported paths relative.
    issues = []
    result = subprocess.run(
        [*cmd, "--set", "extensions.front-matter.enabled=$!True", "scan", *md_files],
        capture_output=True,
        text=True,
        cwd=str(scope.root),
    )
    if result.returncode != 0:
        root = Path(scope.root).resolve()
        for line in result.stdout.splitlines():
            parts = line.split(":", 4)
            if len(parts) >= 5:
                path = Path(parts[0])  # pymarkdown resolves paths to absolute
                if path.is_absolute():
                    try:
                        path = path.relative_to(root)
                    except ValueError:
                        pass
                issues.append(f"{path} — {parts[3].strip()}: {parts[4].strip()} (line {parts[1]})")
    return issues


@statement(
    "markdown_links_absolute",
    help="markdown links/images are absolute URLs, not repo-relative (so they survive on PyPI/npm)",
    builtin=True,
)
def markdown_links_absolute(scope):
    violations = []
    for f in scope.files:
        if not f.endswith(".md"):
            continue
        for target in _MD_LINK.findall(scope.read_text(f) or ""):
            t = target.strip()
            if t.startswith(("http://", "https://", "#", "mailto:")):
                continue
            violations.append(f"{f} — make this link absolute: {t}")
    return violations


def pymarkdown_available() -> bool:
    """Whether the optional markdown linter is installed (used by `henxels doctor`)."""
    return _pymarkdown_cmd() is not None


def _pymarkdown_cmd():
    venv_bin = Path(sys.executable).parent / "pymarkdown"
    if venv_bin.exists():
        return [str(venv_bin)]
    found = shutil.which("pymarkdown")
    return [found] if found else None
