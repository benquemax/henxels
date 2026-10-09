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


WARN_CONTRACT = """
settings:
  warn_about_deleting:
    over_lines: 5
"""


def _seed_lines(root, contract):
    (root / "henxels.yaml").write_text(contract, encoding="utf-8")
    (root / "keep.txt").write_text("important\n", encoding="utf-8")
    (root / "data.txt").write_text("\n".join(f"line {i}" for i in range(20)) + "\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "seed")


def test_warn_about_deleting_warns_but_never_blocks(git_repo):
    _seed_lines(git_repo, WARN_CONTRACT)
    _git(git_repo, "rm", "-q", "keep.txt")
    (git_repo / "data.txt").write_text("line 0\n", encoding="utf-8")
    _git(git_repo, "add", "data.txt")
    code, findings = run_precommit(git_repo)
    assert code == 0
    loss = [f for f in findings if "Information loss" in f.henxel]
    assert len(loss) == 1 and not loss[0].is_block
    assert any("keep.txt" in d for d in loss[0].details)
    assert any("data.txt" in d and "lines removed" in d for d in loss[0].details)
    assert "bless" not in loss[0].steer  # nothing to bless — it is a warning


def test_warn_about_deleting_is_quiet_under_threshold(git_repo):
    _seed_lines(git_repo, WARN_CONTRACT)
    (git_repo / "data.txt").write_text("\n".join(f"line {i}" for i in range(17)) + "\n", encoding="utf-8")
    _git(git_repo, "add", "data.txt")
    code, findings = run_precommit(git_repo)
    assert code == 0
    assert not any("Information loss" in f.henxel for f in findings)


def test_confirm_before_deleting_wins_over_warn(git_repo):
    both = "settings:\n  confirm_before_deleting: true\n  warn_about_deleting: true\n"
    _seed_lines(git_repo, both)
    _git(git_repo, "rm", "-q", "keep.txt")
    code, findings = run_precommit(git_repo)
    assert code == 1
    assert len([f for f in findings if "Information loss" in f.henxel]) == 1
