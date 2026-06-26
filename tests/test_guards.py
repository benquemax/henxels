"""Guards end-to-end (v2): settings-driven delete + push via the hook runners."""

import subprocess

from henxels import bless
from henxels.engine import gitinfo
from henxels.hookrun import run_precommit, run_prepush

CONTRACT = """
settings:
  confirm_before_push: true
  confirm_before_deleting:
    over_lines: 5
"""


def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _seed(root):
    (root / "henxels.yaml").write_text(CONTRACT, encoding="utf-8")
    (root / "keep.txt").write_text("important\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "seed")


def test_precommit_blocks_file_deletion(git_repo):
    _seed(git_repo)
    _git(git_repo, "rm", "-q", "keep.txt")
    code, findings = run_precommit(git_repo)
    assert code == 1
    assert any("deletion" in f.henxel.lower() or "Information loss" in f.henxel for f in findings)


def test_precommit_allows_blessed_deletion(git_repo):
    _seed(git_repo)
    _git(git_repo, "rm", "-q", "keep.txt")
    from henxels.guard import collect_deletions

    dels = collect_deletions(git_repo, 5)
    bless.bless(git_repo, "delete", dels.fingerprint())
    code, _ = run_precommit(git_repo)
    assert code == 0
    assert not bless.is_blessed(git_repo, "delete", dels.fingerprint())


def test_precommit_big_line_removal_blocks(git_repo):
    (git_repo / "henxels.yaml").write_text(CONTRACT, encoding="utf-8")
    f = git_repo / "data.txt"
    f.write_text("\n".join(f"line {i}" for i in range(20)) + "\n", encoding="utf-8")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")
    f.write_text("line 0\n", encoding="utf-8")
    _git(git_repo, "add", "data.txt")
    code, findings = run_precommit(git_repo)
    assert code == 1


def test_prepush_blocks_then_bless(git_repo):
    _seed(git_repo)
    code, findings = run_prepush(git_repo)
    assert code == 1
    assert any("Push is guarded" in f.henxel for f in findings)
    bless.bless(git_repo, "push", gitinfo.head_sha(git_repo))
    assert run_prepush(git_repo)[0] == 0
    assert run_prepush(git_repo)[0] == 1  # token spent
