"""Linked worktrees: `.git` is a *file* there, so nothing may assume `.git/` is a dir.

Hooks are shared across worktrees (git resolves them from the common dir); bless
tokens are per-worktree (the private gitdir under `.git/worktrees/<name>/`).
"""

import subprocess

import pytest

from henxels import bless
from henxels.engine.gitinfo import shadowing_hooks_path
from henxels.hooks import HENXELS_MARKER, hooks_dir, hooks_status, install_hooks


@pytest.fixture
def worktree(git_repo, tmp_path_factory):
    """A linked worktree of git_repo — its `.git` is a file, not a directory."""
    wt = tmp_path_factory.mktemp("wt") / "feature"
    subprocess.run(
        ["git", "worktree", "add", "-q", "-b", "feature", str(wt)],
        cwd=git_repo, check=True, capture_output=True, text=True,
    )
    assert (wt / ".git").is_file()  # the whole point
    return wt


def test_hooks_dir_resolves_to_common_hooks(git_repo, worktree):
    assert hooks_dir(worktree).resolve() == (git_repo / ".git" / "hooks").resolve()


def test_install_and_status_from_worktree(git_repo, worktree):
    result = install_hooks(worktree)
    assert result["pre-commit"] == "installed"

    # landed in the shared hooks dir, so every worktree gets the contract
    hook = git_repo / ".git" / "hooks" / "pre-commit"
    assert HENXELS_MARKER in hook.read_text()

    # doctor's view from inside the worktree agrees — no "run henxels init" loop
    assert hooks_status(worktree) == {"pre-commit": True, "pre-push": True}


def test_bless_tokens_are_worktree_private(git_repo, worktree):
    path = bless.bless(worktree, "delete", "fp")
    assert path.is_file()
    assert bless.consume(worktree, "delete", "fp")
    # minted under the worktree's private gitdir, not the shared one
    assert (git_repo / ".git" / "worktrees") in path.parents
    assert not bless.is_blessed(git_repo, "delete", "fp")


def test_no_false_shadowing_in_worktree(worktree):
    assert shadowing_hooks_path(worktree) is None


def test_hooks_dir_fallback_without_git(tmp_path):
    # not a repo: keep the literal path so install_hooks reports "no-git"
    assert hooks_dir(tmp_path) == tmp_path / ".git" / "hooks"
    assert install_hooks(tmp_path) == {"pre-commit": "no-git", "pre-push": "no-git"}
