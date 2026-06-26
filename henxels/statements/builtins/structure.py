"""Structure statements: which files/folders may, must, or must not exist.

REQUIRE (allowed_filetypes is MATCH; required_* are AND), FORBID (none of these).
"""

from __future__ import annotations

from henxels.statements.builtins._helpers import bare_name, file_matches
from henxels.statements.registry import as_list, statement
from henxels.util.glob import glob_match


@statement("allowed_filetypes", help="every file is one of these extensions/globs (list = any of)", builtin=True)
def allowed_filetypes(param, scope):
    patterns = as_list(param)
    violations = []
    for f in scope.files:
        if not any(file_matches(p, f) for p in patterns):
            violations.append(f"{f} — should be {' or '.join(patterns)}")
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


@statement("required_subfolders", help="these subfolders must exist in the location (list = all)", builtin=True)
def required_subfolders(param, scope):
    names = as_list(param)
    violations = []
    for loc in scope.locations:
        for name in names:
            rel = f"{loc}/{name}" if loc else name
            if not scope.is_dir(rel):
                violations.append(f"create the folder {rel}/")
    return violations


@statement("only_these_subfolders", help="only these immediate subfolders may exist", builtin=True)
def only_these_subfolders(param, scope):
    allowed = set(as_list(param))
    violations = []
    for loc in scope.locations:
        for sub in scope.subfolders_of(loc):
            if sub not in allowed:
                where = f"{loc}/{sub}" if loc else sub
                violations.append(f"{where}/ — remove or relocate (allowed: {', '.join(sorted(allowed))})")
    return violations


@statement("forbidden_files", help="none of these files/globs may exist", builtin=True)
def forbidden_files(param, scope):
    patterns = as_list(param)
    violations = []
    for f in scope.files:
        name = f.rsplit("/", 1)[-1]
        for p in patterns:
            if glob_match(p, f) or glob_match(p, name) or bare_name(p, name):
                violations.append(f"{f} — forbidden ({p}); remove it")
                break
    return violations


@statement("forbidden_subfolders", help="none of these subfolders may exist", builtin=True)
def forbidden_subfolders(param, scope):
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
