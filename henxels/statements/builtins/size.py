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
