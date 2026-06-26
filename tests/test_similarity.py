"""Similarity warnings over the committed corpus (v2, settings-driven)."""

import subprocess

from henxels.similarity import find_duplicates, warn_similar

BODY = "\n".join(f"def func_{i}():\n    return {i} * 2 + 1" for i in range(30))


def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def test_detects_near_duplicate(git_repo):
    (git_repo / "original.py").write_text(BODY + "\n", encoding="utf-8")
    _git(git_repo, "add", "original.py")
    _git(git_repo, "commit", "-q", "-m", "add")
    (git_repo / "copy.py").write_text(BODY + "\n# tiny change\n", encoding="utf-8")

    dups = find_duplicates(git_repo, ["copy.py"], threshold=0.85)
    assert dups and dups[0][1] == "original.py"


def test_warn_similar_excludes(git_repo):
    (git_repo / "a__init__.py").write_text(BODY + "\n", encoding="utf-8")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")
    (git_repo / "__init__.py").write_text(BODY + "\n", encoding="utf-8")

    sim = {"above": 0.85, "ignore": ["**/__init__.py", "*__init__.py"]}
    assert warn_similar(sim, git_repo, ["__init__.py"]) == []


def test_warn_similar_off_when_none(git_repo):
    assert warn_similar(None, git_repo, ["anything.py"]) == []


def test_warn_similar_finding_is_warning(git_repo):
    (git_repo / "original.py").write_text(BODY + "\n", encoding="utf-8")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")
    (git_repo / "copy.py").write_text(BODY + "\n", encoding="utf-8")

    findings = warn_similar({"above": 0.85}, git_repo, ["copy.py"])
    assert findings and not findings[0].is_block
    assert "similar to original.py" in findings[0].details[0]
