"""The built-in statement library, grouped by concern.

Importing this package registers every built-in (each category module runs its
``@statement`` decorators on import). Add a new built-in to the fitting module:

    naming      file names                 (filename_casing, filename_matches_regex)
    structure   where files/folders live   (allowed_filetypes, required_*, forbidden_*, …)
    content     what's inside files        (required_frontmatter, frontmatter_*, markdown_lint)
    links       cross-page navigation      (links_resolve, links_are_relative, min_outbound_links, referenced_in)
    size        per-file line budgets      (max_lines)
    security    things that must not ship  (no_secrets)
    history     rules about change         (append_only, immutable, bump_updated_on_change)
    meta        the statement library      (well_formed_statements)
    commands    git-stage command gates    (run_before_commit, run_before_push)
"""

from henxels.statements.builtins import (  # noqa: F401  (imported for registration)
    commands,
    content,
    history,
    links,
    meta,
    naming,
    security,
    size,
    structure,
)

# Re-exported for tests / direct callers (these aren't run via name-injection).
from henxels.statements.builtins.content import markdown_lint
from henxels.statements.builtins.meta import well_formed_statements

__all__ = ["markdown_lint", "well_formed_statements"]
