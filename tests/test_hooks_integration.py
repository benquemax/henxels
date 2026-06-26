"""Real git invokes the installed hook script (not just the Python runner)."""

import subprocess

import pytest

from henxels.hooks import install_hooks

CONTRACT = """
henxels: 1
guards:
  delete:
    mode: bless
    line_threshold: 5
"""


def _git(root, *args, check=True):
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=check
    )


def test_real_precommit_blocks_deletion(git_repo):
    (git_repo / "henxels.yaml").write_text(CONTRACT, encoding="utf-8")
    (git_repo / "keep.txt").write_text("important\n", encoding="utf-8")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")

    install_hooks(git_repo)

    _git(git_repo, "rm", "-q", "keep.txt")
    # The commit must be rejected by the henxels pre-commit hook.
    result = _git(git_repo, "commit", "-m", "drop file", check=False)
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "guard:delete" in combined or "information loss" in combined


def test_real_precommit_allows_after_bless(git_repo):
    (git_repo / "henxels.yaml").write_text(CONTRACT, encoding="utf-8")
    (git_repo / "keep.txt").write_text("important\n", encoding="utf-8")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")
    install_hooks(git_repo)
    _git(git_repo, "rm", "-q", "keep.txt")

    blessed = subprocess.run(
        ["henxels", "bless", "delete"], cwd=git_repo, capture_output=True, text=True
    )
    assert blessed.returncode == 0

    result = _git(git_repo, "commit", "-m", "drop file", check=False)
    assert result.returncode == 0, result.stdout + result.stderr
