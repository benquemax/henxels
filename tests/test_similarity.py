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


def test_bulk_import_is_summarised_not_dumped(git_repo):
    # A bulk import (an archive, a vendored tree, generated variations) can make
    # every added file resemble another. One warning per pair buries the commit
    # output in thousands of lines nobody reads, so past a cap we summarise.
    (git_repo / "original.py").write_text(BODY + "\n", encoding="utf-8")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")
    names = []
    for i in range(30):
        name = f"copy{i}.py"
        (git_repo / name).write_text(f"{BODY}\n# {i}\n", encoding="utf-8")
        names.append(name)

    findings = warn_similar({"above": 0.85, "at_most": 5}, git_repo, names)

    assert len(findings) == 6  # 5 detailed + 1 summary
    assert "25 more" in findings[-1].details[0]
    assert not any(f.is_block for f in findings)


def test_cap_is_not_applied_below_the_limit(git_repo):
    (git_repo / "original.py").write_text(BODY + "\n", encoding="utf-8")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")
    (git_repo / "copy.py").write_text(BODY + "\n", encoding="utf-8")

    findings = warn_similar({"above": 0.85, "at_most": 5}, git_repo, ["copy.py"])
    assert len(findings) == 1
    assert "more" not in findings[0].details[0]
