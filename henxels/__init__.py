"""henxels — external structure that gives shape to your project.

Custom checks register with the ``@statement`` decorator:

    from henxels import statement

    @statement("max_lines")
    def max_lines(limit, scope):
        return [f"{f} is too long" for f in scope.files
                if scope.line_count(f) > limit]
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _package_version

from henxels.statements import Scope, as_list, statement

try:
    # Single source of truth: pyproject.toml. A hand-maintained literal here sat
    # at 0.2.0 while the package shipped 0.7.0 — never again.
    __version__ = _package_version("henxels")
except PackageNotFoundError:  # a checkout used without being installed
    __version__ = "0.0.0.dev0"

__all__ = ["statement", "Scope", "as_list", "__version__"]
