"""Similarity warnings over the committed corpus."""

import subprocess

from henxels.config.load import Config
from henxels.similarity import find_duplicates, similarity_findings

BODY = "\n".join(f"def func_{i}():\n    return {i} * 2 + 1" for i in range(30))


def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def test_detects_near_duplicate_of_committed(git_repo):
    (git_repo / "original.py").write_text(BODY + "\n", encoding="utf-8")
    _git(git_repo, "add", "original.py")
    _git(git_repo, "commit", "-q", "-m", "add original")

    # A new, uncommitted near-copy.
    (git_repo / "copy.py").write_text(BODY + "\n# tiny change\n", encoding="utf-8")

    dups = find_duplicates(git_repo, ["copy.py"], threshold=0.85)
    assert dups and dups[0][1] == "original.py"
    assert dups[0][2] >= 0.85


def test_excluded_names_skipped(git_repo):
    (git_repo / "a__init__.py").write_text(BODY + "\n", encoding="utf-8")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")
    (git_repo / "__init__.py").write_text(BODY + "\n", encoding="utf-8")

    cfg = Config(similarity={"warn_above": 0.85, "exclude": ["**/__init__.py", "*__init__.py"]})
    findings = similarity_findings(cfg, git_repo, ["__init__.py"])
    assert findings == []


def test_distinct_files_no_warning(git_repo):
    (git_repo / "one.py").write_text("print('hello world')\n", encoding="utf-8")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")
    (git_repo / "two.py").write_text("x = sum(range(1000))\n", encoding="utf-8")

    cfg = Config(similarity={"warn_above": 0.85})
    findings = similarity_findings(cfg, git_repo, ["two.py"])
    assert findings == []


def test_similarity_disabled_when_unconfigured(git_repo):
    cfg = Config()  # no similarity block
    assert similarity_findings(cfg, git_repo, ["anything.py"]) == []


def test_finding_is_warning(git_repo):
    (git_repo / "original.py").write_text(BODY + "\n", encoding="utf-8")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")
    (git_repo / "copy.py").write_text(BODY + "\n", encoding="utf-8")

    cfg = Config(similarity={"warn_above": 0.85})
    findings = similarity_findings(cfg, git_repo, ["copy.py"])
    assert findings and not findings[0].is_block
    assert findings[0].henxel == "similarity"
