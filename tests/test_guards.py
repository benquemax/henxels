"""Guards end-to-end: delete (files + lines) and push, via the hook runners."""

import subprocess

from henxels import bless
from henxels.config.load import Config
from henxels.engine import gitinfo
from henxels.hookrun import run_precommit, run_prepush
from henxels.rules.guard import collect_deletions, guard_mode

CONTRACT = """
henxels: 1
guards:
  push: bless
  delete:
    mode: bless
    line_threshold: 5
"""


def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _write_contract(root):
    (root / "henxels.yaml").write_text(CONTRACT, encoding="utf-8")


def test_guard_mode_parsing():
    cfg = Config(guards={"push": "bless", "delete": {"mode": "bless", "line_threshold": 9}})
    assert guard_mode(cfg, "push") == "bless"
    assert guard_mode(cfg, "delete") == "bless"
    assert guard_mode(cfg, "commit") == "off"


def test_precommit_blocks_file_deletion(git_repo):
    _write_contract(git_repo)
    victim = git_repo / "keep.txt"
    victim.write_text("important\n", encoding="utf-8")
    _git(git_repo, "add", "keep.txt", "henxels.yaml")
    _git(git_repo, "commit", "-q", "-m", "add")
    _git(git_repo, "rm", "-q", "keep.txt")  # stage a deletion

    code, findings = run_precommit(git_repo)
    assert code == 1
    assert any(f.henxel == "guard:delete" for f in findings)


def test_precommit_allows_blessed_deletion(git_repo):
    _write_contract(git_repo)
    victim = git_repo / "keep.txt"
    victim.write_text("important\n", encoding="utf-8")
    _git(git_repo, "add", "keep.txt", "henxels.yaml")
    _git(git_repo, "commit", "-q", "-m", "add")
    _git(git_repo, "rm", "-q", "keep.txt")

    cfg = Config(guards={"push": "bless", "delete": {"mode": "bless", "line_threshold": 5}})
    dels = collect_deletions(cfg, git_repo)
    bless.bless(git_repo, "delete", dels.fingerprint())

    code, findings = run_precommit(git_repo)
    assert code == 0
    # token spent
    assert not bless.is_blessed(git_repo, "delete", dels.fingerprint())


def test_precommit_blocks_big_line_removal(git_repo):
    _write_contract(git_repo)
    f = git_repo / "data.txt"
    f.write_text("\n".join(f"line {i}" for i in range(20)) + "\n", encoding="utf-8")
    _git(git_repo, "add", "data.txt", "henxels.yaml")
    _git(git_repo, "commit", "-q", "-m", "seed")
    f.write_text("line 0\n", encoding="utf-8")  # remove ~19 lines
    _git(git_repo, "add", "data.txt")

    code, findings = run_precommit(git_repo)
    assert code == 1
    assert any("lines removed" in f.message for f in findings if f.henxel == "guard:delete")


def test_precommit_ignores_small_edits(git_repo):
    _write_contract(git_repo)
    f = git_repo / "data.txt"
    f.write_text("\n".join(f"line {i}" for i in range(20)) + "\n", encoding="utf-8")
    _git(git_repo, "add", "data.txt", "henxels.yaml")
    _git(git_repo, "commit", "-q", "-m", "seed")
    # remove just 2 lines (under threshold)
    f.write_text("\n".join(f"line {i}" for i in range(18)) + "\n", encoding="utf-8")
    _git(git_repo, "add", "data.txt")

    code, findings = run_precommit(git_repo)
    assert code == 0
    assert not any(f.henxel == "guard:delete" for f in findings)


def test_prepush_blocks_then_bless_allows(git_repo):
    _write_contract(git_repo)
    _git(git_repo, "add", "henxels.yaml")
    _git(git_repo, "commit", "-q", "-m", "contract")

    code, findings = run_prepush(git_repo)
    assert code == 1
    assert any(f.henxel == "guard:push" for f in findings)

    fp = gitinfo.head_sha(git_repo)
    bless.bless(git_repo, "push", fp)
    code2, _ = run_prepush(git_repo)
    assert code2 == 0
    # token spent — a second push is guarded again
    code3, _ = run_prepush(git_repo)
    assert code3 == 1
