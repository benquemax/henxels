"""History statements: rules about how a file may *change*, not just its snapshot.

These ask for the ``diff`` injectable. Outside a staged context (``check --all``) the
diff is None and they pass — there's no change to judge.
"""

from __future__ import annotations

from henxels.statements.builtins._helpers import parse_frontmatter
from henxels.statements.registry import statement


@statement("append_only", help="staged edits only add lines to the end; existing lines are never changed", builtin=True)
def append_only(param, scope, diff):
    if param is False or diff is None:
        return []
    violations = []
    for f in scope.files:
        if f not in diff.modified:
            continue
        old = diff.old_text(f) or ""
        new = diff.new_text(f)
        if new is not None and not new.startswith(old):
            violations.append(f"{f} — append-only: add to the end; don't change or remove existing lines")
    return violations


@statement("immutable", help="files here can be added but never modified once committed", builtin=True)
def immutable(param, scope, diff):
    if param is False or diff is None:
        return []
    return [
        f"{f} — immutable; add a new file instead of editing this one"
        for f in scope.files
        if f in diff.modified
    ]


@statement("bump_updated_on_change", help="when a page's content changes, its date field must change too", builtin=True)
def bump_updated_on_change(param, scope, diff):
    field = param if isinstance(param, str) else "updated"
    if diff is None:
        return []
    violations = []
    for f in scope.files:
        if not f.endswith(".md") or f not in diff.modified:
            continue
        old = parse_frontmatter(diff.old_text(f))
        new = parse_frontmatter(diff.new_text(f))
        if field in new and old.get(field) == new.get(field):
            violations.append(f"{f} — content changed but '{field}' wasn't bumped; update the frontmatter date")
    return violations
