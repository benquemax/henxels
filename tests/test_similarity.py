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


def test_exact_duplicate_scores_full_similarity(git_repo):
    (git_repo / "original.py").write_text(BODY + "\n", encoding="utf-8")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")
    (git_repo / "copy.py").write_text(BODY + "\n", encoding="utf-8")

    dups = find_duplicates(git_repo, ["copy.py"], threshold=0.85)
    assert dups == [("copy.py", "original.py", 1.0)]


def test_unrelated_files_do_not_match(git_repo):
    # Same language, same alphabet, no shared lines → not similar. (Guards
    # against char-frequency metrics that score all same-language files alike.)
    (git_repo / "original.py").write_text(BODY + "\n", encoding="utf-8")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")
    other = "\n".join(f"def helper_{i}(x):\n    return x - {i}" for i in range(30))
    (git_repo / "unrelated.py").write_text(other + "\n", encoding="utf-8")

    assert find_duplicates(git_repo, ["unrelated.py"], threshold=0.85) == []


def test_deep_scan_catches_rewrite_sharing_no_lines(git_repo):
    # Docs re-written from scratch about the same thing share vocabulary and
    # structure but rarely a single identical line. A changed-file (deep) scan
    # must still catch that; the whole-repo (fast) scan explicitly does not.
    lines = [f"The endpoint /api/v1/resource_{i} returns a json object with id {i}." for i in range(40)]
    (git_repo / "api.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")
    rewrite = [li.replace("returns a", "always returns a") for li in lines]  # no line survives
    (git_repo / "api-docs.md").write_text("\n".join(rewrite) + "\n", encoding="utf-8")

    assert find_duplicates(git_repo, ["api-docs.md"], threshold=0.85)  # deep is the default
    assert find_duplicates(git_repo, ["api-docs.md"], threshold=0.85, deep=False) == []


def test_whole_corpus_scan_is_fast(git_repo):
    # 300 mutually-dissimilar files, every file both candidate and corpus —
    # the `check --all` shape that used to be O(N²) pairwise diffs (minutes).
    import time

    names = []
    for i in range(300):
        name = f"file_{i}.py"
        body = "\n".join(f"def fn_{i}_{j}():\n    return {i} * {j}" for j in range(40))
        (git_repo / name).write_text(body + "\n", encoding="utf-8")
        names.append(name)
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")

    start = time.perf_counter()
    dups = find_duplicates(git_repo, names, threshold=0.85, deep=False)
    assert time.perf_counter() - start < 5.0
    assert dups == []


def test_low_threshold_survives_length_difference(git_repo):
    # Guards the pre-filters against threshold-blind constants: at above=0.7 a
    # 100-line file truncated to 62 lines (ratio ≈ 0.77) must still surface,
    # even though the lengths differ by ~60% relative to the shorter file.
    lines = [f"some meaningful line number {i}" for i in range(100)]
    (git_repo / "original.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")
    (git_repo / "truncated.txt").write_text("\n".join(lines[:62]) + "\n", encoding="utf-8")

    dups = find_duplicates(git_repo, ["truncated.txt"], threshold=0.7)
    assert dups and dups[0][1] == "original.txt"


def test_cap_is_not_applied_below_the_limit(git_repo):
    (git_repo / "original.py").write_text(BODY + "\n", encoding="utf-8")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")
    (git_repo / "copy.py").write_text(BODY + "\n", encoding="utf-8")

    findings = warn_similar({"above": 0.85, "at_most": 5}, git_repo, ["copy.py"])
    assert len(findings) == 1
    assert "more" not in findings[0].details[0]
# --- performance: the scan is complete, and fast because of the algorithm ---

def _count_ratio_calls(monkeypatch):
    import difflib

    calls = {"n": 0}
    original = difflib.SequenceMatcher.ratio

    def counting(self):
        calls["n"] += 1
        return original(self)

    monkeypatch.setattr(difflib.SequenceMatcher, "ratio", counting)
    return calls


def test_stops_at_first_match(git_repo, monkeypatch):
    # A warning needs *a* match, not the closest one — one hit ends the scan
    # for that candidate instead of diffing the whole corpus for an argmax.
    for i in range(10):
        (git_repo / f"gen_{i}.py").write_text(BODY + f"\n# rev {i}\n", encoding="utf-8")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")
    (git_repo / "copy.py").write_text(BODY + "\n# rev x\n", encoding="utf-8")

    calls = _count_ratio_calls(monkeypatch)
    dups = find_duplicates(git_repo, ["copy.py"], threshold=0.85)
    assert dups and dups[0][2] >= 0.85
    assert calls["n"] == 1


def test_scan_is_complete_by_default(git_repo):
    # No silent work caps: without an explicit budget every candidate is scanned.
    (git_repo / "original.py").write_text(BODY + "\n", encoding="utf-8")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")
    (git_repo / "copy.py").write_text(BODY + "\n", encoding="utf-8")

    dups = find_duplicates(git_repo, ["copy.py"], threshold=0.85)
    assert not dups.truncated


def test_explicit_budget_flags_partial_results(git_repo):
    (git_repo / "original.py").write_text(BODY + "\n", encoding="utf-8")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")
    (git_repo / "copy.py").write_text(BODY + "\n", encoding="utf-8")

    dups = find_duplicates(git_repo, ["copy.py"], threshold=0.85, budget_seconds=0)
    assert list(dups) == []
    assert dups.truncated


def test_warn_similar_notes_exhausted_budget(git_repo):
    (git_repo / "original.py").write_text(BODY + "\n", encoding="utf-8")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")
    (git_repo / "copy.py").write_text(BODY + "\n", encoding="utf-8")

    findings = warn_similar({"above": 0.85, "budget": 0}, git_repo, ["copy.py"])
    assert len(findings) == 1 and not findings[0].is_block
    assert "budget" in findings[0].details[0]
    assert "ignore" in findings[0].details[0]
