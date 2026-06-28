"""History statements: rules about how a file may *change*, not just its snapshot.

These ask for the ``diff`` injectable. Outside a staged context (``check --all``) the
diff is None and they pass — there's no change to judge.
"""

from __future__ import annotations

from henxels.statements.builtins._helpers import parse_frontmatter
from henxels.statements.registry import as_list, statement
from henxels.util.glob import glob_match


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


@statement(
    "must_be_in_sync",
    help="commit-time reminder: groups of files/folders that change together — warns if some did and some didn't",
    builtin=True,
)
def must_be_in_sync(param, diff):
    if diff is None:
        return None
    groups = param if isinstance(param, list) else []
    if groups and all(isinstance(g, str) for g in groups):
        groups = [groups]  # a single group given as a flat list: [a, b]
    staged = diff.added | diff.modified | diff.deleted
    out = []
    for group in groups:
        members = as_list(group)
        if len(members) < 2:
            continue
        changed = [m for m in members if any(glob_match(m, f) for f in staged)]
        if not changed or len(changed) == len(members):
            continue  # group untouched, or everything moved together
        missing = [m for m in members if m not in changed]
        out.append(f"{', '.join(changed)} changed but {', '.join(missing)} didn't — keep them in sync")
    return out or None


@statement(
    "changed_with",
    help="commit-time reminder: when files matching `when` are staged, files matching `expect` should change too (directional)",
    builtin=True,
)
def changed_with(param, diff):
    if diff is None or not isinstance(param, dict):
        return None
    when = as_list(param.get("when"))
    expect = as_list(param.get("expect"))
    if not when or not expect:
        return None
    staged = diff.added | diff.modified | diff.deleted
    if not any(glob_match(p, f) for f in staged for p in when):
        return None  # the trigger files weren't touched — stay quiet
    if any(glob_match(p, f) for f in staged for p in expect):
        return None  # a companion changed too — satisfied
    return (
        f"you changed {', '.join(when)} but none of {', '.join(expect)} — "
        f"update them in this commit if the change affects them"
    )


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
