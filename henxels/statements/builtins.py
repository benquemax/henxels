"""The built-in statement vocabulary.

Each function takes name-injected args and returns its violations (empty = pass).
List semantics are implied by the name:

    MATCH   (files_are, casing, files_match_regex)   list = OR  (any is acceptable)
    REQUIRE (frontmatter_has, required_files,         list = AND (all required)
             required_folders, only_these_folders)
    FORBID  (forbidden_files, forbidden_folders)      list = none of these
"""

from __future__ import annotations

import re

import yaml

from henxels.casing import NAMING_CONVENTIONS
from henxels.statements.registry import as_list, statement
from henxels.util.glob import glob_match

# --- MATCH statements ----------------------------------------------------

@statement("casing", help="file names use this naming convention (snake_case, kebab-case, …)", builtin=True)
def casing(param, scope):
    conventions = as_list(param)
    unknown = [c for c in conventions if c not in NAMING_CONVENTIONS]
    if unknown:
        return [f"unknown casing {unknown[0]!r} (use {', '.join(NAMING_CONVENTIONS)})"]
    violations = []
    for f in scope.files:
        if not any(scope.matches_casing(f, c) for c in conventions):
            violations.append(f"{f} — rename to {' or '.join(conventions)}")
    return violations


@statement("files_are", help="every file matches an extension or glob (list = any of)", builtin=True)
def files_are(param, scope):
    patterns = as_list(param)
    violations = []
    for f in scope.files:
        if not any(_file_matches(p, f) for p in patterns):
            violations.append(f"{f} — should be {' or '.join(patterns)}")
    return violations


@statement("files_match_regex", help="every file name matches a regex (list = any of)", builtin=True)
def files_match_regex(param, scope):
    regexes = [re.compile(p) for p in as_list(param)]
    violations = []
    for f in scope.files:
        name = f.rsplit("/", 1)[-1]
        if not any(rx.search(name) for rx in regexes):
            violations.append(f"{f} — name must match the required pattern")
    return violations


# --- REQUIRE statements --------------------------------------------------

@statement("frontmatter_has", help="markdown files declare these frontmatter keys (list = all)", builtin=True)
def frontmatter_has(param, scope):
    keys = as_list(param)
    violations = []
    for f in scope.files:
        if not f.endswith(".md"):
            continue
        meta = _frontmatter(scope.read_text(f))
        for key in keys:
            if key not in meta:
                violations.append(f"{f} — add frontmatter key '{key}'")
    return violations


@statement("required_files", help="these files must exist in the location (list = all)", builtin=True)
def required_files(param, scope):
    names = as_list(param)
    violations = []
    for loc in scope.locations:
        for name in names:
            rel = f"{loc}/{name}" if loc else name
            if not scope.exists(rel):
                violations.append(f"create {rel}")
    return violations


@statement("required_folders", help="these folders must exist in the location (list = all)", builtin=True)
def required_folders(param, scope):
    names = as_list(param)
    violations = []
    for loc in scope.locations:
        for name in names:
            rel = f"{loc}/{name}" if loc else name
            if not scope.is_dir(rel):
                violations.append(f"create the folder {rel}/")
    return violations


@statement("only_these_folders", help="only these immediate subfolders may exist", builtin=True)
def only_these_folders(param, scope):
    allowed = set(as_list(param))
    violations = []
    for loc in scope.locations:
        for sub in scope.subfolders_of(loc):
            if sub not in allowed:
                where = f"{loc}/{sub}" if loc else sub
                violations.append(f"{where}/ — remove or relocate (allowed: {', '.join(sorted(allowed))})")
    return violations


# --- FORBID / existence statements --------------------------------------

@statement("forbidden_files", help="none of these files/globs may exist", builtin=True)
def forbidden_files(param, scope):
    patterns = as_list(param)
    violations = []
    for f in scope.files:
        name = f.rsplit("/", 1)[-1]
        for p in patterns:
            if glob_match(p, f) or glob_match(p, name) or _bare_name(p, name):
                violations.append(f"{f} — forbidden ({p}); remove it")
                break
    return violations


@statement("forbidden_folders", help="none of these folders may exist", builtin=True)
def forbidden_folders(param, scope):
    names = as_list(param)
    violations = []
    for loc in scope.locations:
        for name in names:
            rel = f"{loc}/{name}" if loc else name
            if scope.is_dir(rel):
                violations.append(f"{rel}/ — forbidden folder; remove it")
    return violations


@statement("must_not_exist", help="the location(s) must not exist at all", builtin=True)
def must_not_exist(param, scope):
    if param is False:
        return []
    violations = []
    for loc in scope.locations:
        if loc and scope.exists(loc):
            violations.append(f"{loc} — must not exist; remove it")
    return violations


# --- COMMAND gates (executed by the hooks, skipped during `check`) -------

@statement("run_before_commit", stage="pre_commit", help="command that must pass before a commit", builtin=True)
def run_before_commit(param, scope):  # pragma: no cover - executed by hooks
    return []


@statement("run_before_push", stage="pre_push", help="command that must pass before a push", builtin=True)
def run_before_push(param, scope):  # pragma: no cover - executed by hooks
    return []


# --- helpers -------------------------------------------------------------

def _file_matches(pattern: str, path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    if pattern.startswith(".") and "*" not in pattern and "?" not in pattern:
        return name.endswith(pattern)  # ".md" means extension
    return glob_match(pattern, name) or glob_match(pattern, path)


def _bare_name(pattern: str, name: str) -> bool:
    if "/" in pattern or "*" in pattern or "?" in pattern:
        return False
    return name == pattern


def _frontmatter(text: str | None) -> dict:
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
