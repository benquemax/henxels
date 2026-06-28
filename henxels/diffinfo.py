"""The staged-diff view handed to git-diff-aware statements.

Some henxels can only be judged against *change*, not a snapshot: "did the body change
without bumping ``updated``?", "was an append-only log edited?", "was an immutable
source modified?". Those statements ask for the ``diff`` injectable — a StagedDiff that
knows which files were added/modified/deleted and can read both the HEAD and the staged
version of a file. Outside a staged context (e.g. ``check --all``) the diff is ``None``
and such statements simply pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from henxels.engine import gitinfo


@dataclass
class StagedDiff:
    root: Path
    added: frozenset[str]
    modified: frozenset[str]
    deleted: frozenset[str]

    @property
    def changed(self) -> frozenset[str]:
        return self.added | self.modified

    def old_text(self, rel: str) -> str | None:
        """The file's content at HEAD (None if newly added)."""
        return gitinfo.file_at_head(self.root, rel)

    def new_text(self, rel: str) -> str | None:
        """The file's staged content (what would be committed)."""
        return gitinfo.file_in_index(self.root, rel)


def staged_diff(root: Path | str) -> StagedDiff | None:
    """Build the staged diff, or None if this isn't a git repo."""
    if not gitinfo.is_git_repo(root):
        return None
    added: set[str] = set()
    modified: set[str] = set()
    deleted: set[str] = set()
    for status, path in gitinfo.staged_name_status(root):
        if status == "A":
            added.add(path)
        elif status == "D":
            deleted.add(path)
        else:  # M, R (rename → treat as a modification of the new path)
            modified.add(path)
    return StagedDiff(Path(root), frozenset(added), frozenset(modified), frozenset(deleted))
