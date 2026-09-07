"""Size statements: keep individual files small enough to stay workable.

(File-size *warnings* across the whole repo live in settings as
``warn_about_large_files``; this is the scoped, structural line-budget rule.)
"""

from __future__ import annotations

from henxels.statements.registry import statement


@statement("max_lines", help="each file in scope stays under a line budget", builtin=True)
def max_lines(param, file, scope):
    limit = int(param)
    count = scope.line_count(file)
    if count > limit:
        return f"split {file}: keep it under {limit} lines (now {count})"


@statement("max_files", help="a location holds at most N files directly (subfolders not counted)", builtin=True)
def max_files(param, scope):
    """The folder-level twin of max_lines: a working set stays small while history
    lives below it. Only files *directly* in each location count; `except:` removes
    files (an index, say) from the tally. Motivating case: a journals/ folder that
    may hold one current month while earlier months sit in journals/archive/."""
    limit = int(param)
    violations = []
    for loc in scope.locations:
        prefix = f"{loc}/" if loc else ""
        direct = [f for f in scope.files if f.startswith(prefix) and "/" not in f[len(prefix):]]
        if len(direct) > limit:
            where = f"{loc}/" if loc else "./"
            names = ", ".join(sorted(f[len(prefix):] for f in direct))
            violations.append(f"{where} — {len(direct)} files directly inside, at most {limit} allowed ({names}); "
                              "move the rest into a subfolder")
    return violations
