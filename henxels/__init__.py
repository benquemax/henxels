"""henxels — external structure that gives shape to your project.

Custom checks register with the ``@statement`` decorator:

    from henxels import statement

    @statement("max_lines")
    def max_lines(limit, scope):
        return [f"{f} is too long" for f in scope.files
                if scope.line_count(f) > limit]
"""

from henxels.statements import Scope, as_list, statement

__version__ = "0.2.0"

__all__ = ["statement", "Scope", "as_list", "__version__"]
