"""make_sure_that — a natural-language henxel judged by a language model.

The judge is faked here (no network); what's under test is the statement's contract:
diff-only evidence, fail-open, confidence-driven severity, caching.
"""

from __future__ import annotations

import subprocess

import pytest

from henxels.contract import Contract, Henxel
from henxels.diffinfo import staged_diff
from henxels.findings import WARN, Advisory
from henxels.judge import Verdict
from henxels.runner import run_contract
from henxels.statements.builtins import judgement
from henxels.statements.builtins.judgement import build_evidence, make_sure_that
from henxels.statements.scope import build_scope


def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)


def _repo(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    return tmp_path


def _write(root, rel, content):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _commit(root, rel, content):
    _write(root, rel, content)
    _git(root, "add", rel)
    _git(root, "commit", "-qm", "seed")


def _stage(root, rel, content):
    _write(root, rel, content)
    _git(root, "add", rel)


class FakeJudge:
    def __init__(self, *verdicts):
        self.verdicts, self.calls = list(verdicts), []

    def judge(self, sentence, why, evidence, references=None):
        self.calls.append((sentence, why, evidence, references or {}))
        return self.verdicts.pop(0) if self.verdicts else Verdict(holds=True, reason="fine")


@pytest.fixture
def fake(monkeypatch):
    holder = {}

    def install(*verdicts):
        j = FakeJudge(*verdicts)
        holder["j"] = j
        monkeypatch.setattr(judgement, "make_judge", lambda settings: j)
        return j

    return install


SETTINGS = {"judge": {"base_url": "http://fake/v1", "model": "m"}}


def _hx(text="Behaviour changes are described in the docs", why="", level="block"):
    return Henxel(text=text, level=level, why=why, statements={"make_sure_that": True})


def _scope(root, files, locations=("./*",), settings=SETTINGS):
    return build_scope(list(locations), files, root, settings)


# --- evidence -----------------------------------------------------------------


def test_evidence_is_a_unified_diff_of_changed_files_in_scope(tmp_path):
    r = _repo(tmp_path)
    _commit(r, "a.py", "x = 1\n")
    _stage(r, "a.py", "x = 2\n")
    _stage(r, "new.md", "hello\n")
    _write(r, "untracked.txt", "nope")
    diff = staged_diff(r)
    ev = build_evidence(["a.py", "new.md", "untracked.txt"], diff)
    assert "--- a/a.py" in ev and "+++ b/a.py" in ev
    assert "-x = 1" in ev and "+x = 2" in ev
    assert "+++ b/new.md" in ev and "+hello" in ev
    assert "untracked" not in ev  # not staged → not evidence


def test_evidence_mentions_deletions(tmp_path):
    r = _repo(tmp_path)
    _commit(r, "gone.md", "bye\n")
    _git(r, "rm", "-q", "gone.md")
    ev = build_evidence(["gone.md"], staged_diff(r))
    assert "gone.md" in ev and "deleted" in ev


def test_evidence_empty_when_nothing_in_scope_changed(tmp_path):
    r = _repo(tmp_path)
    _commit(r, "a.py", "x = 1\n")
    _stage(r, "other/b.py", "y\n")
    assert build_evidence(["a.py"], staged_diff(r)) == ""


# --- the statement ------------------------------------------------------------


def test_passes_without_diff(fake, tmp_path):
    j = fake()
    assert make_sure_that(True, _hx(), _scope(tmp_path, ["a.py"]), None, SETTINGS) is None
    assert j.calls == []


def test_passes_quietly_when_scope_untouched(fake, tmp_path):
    r = _repo(tmp_path)
    _commit(r, "a.py", "x\n")
    _stage(r, "elsewhere.txt", "y\n")
    j = fake()
    scope = _scope(r, ["a.py", "elsewhere.txt"], locations=["./a.py"])
    assert make_sure_that(True, _hx(), scope, staged_diff(r), SETTINGS) is None
    assert j.calls == []  # no tokens spent when there's nothing to judge


def test_true_uses_the_henxel_sentence_and_why(fake, tmp_path):
    r = _repo(tmp_path)
    _stage(r, "a.py", "x\n")
    j = fake(Verdict(holds=True, confidence=0.99, reason="ok"))
    out = make_sure_that(True, _hx(why="docs that lie are worse than none"), _scope(r, ["a.py"]), staged_diff(r), SETTINGS)
    assert out is None
    sentence, why, evidence, _ = j.calls[0]
    assert sentence == "Behaviour changes are described in the docs"
    assert why == "docs that lie are worse than none"
    assert "+x" in evidence


def test_string_param_is_its_own_statement(fake, tmp_path):
    r = _repo(tmp_path)
    _stage(r, "a.py", "x\n")
    j = fake()
    make_sure_that("every public function has a docstring", _hx(), _scope(r, ["a.py"]), staged_diff(r), SETTINGS)
    assert j.calls[0][0] == "every public function has a docstring"


def test_list_param_judges_each_sentence(fake, tmp_path):
    r = _repo(tmp_path)
    _stage(r, "a.py", "x\n")
    j = fake(Verdict(holds=True, reason="a"), Verdict(holds=False, confidence=0.95, reason="no tests"))
    out = make_sure_that(["one", "two"], _hx(), _scope(r, ["a.py"]), staged_diff(r), SETTINGS)
    assert [c[0] for c in j.calls] == ["one", "two"]
    assert len(out) == 1 and "no tests" in out[0]


def test_failure_with_high_confidence_is_a_plain_instruction(fake, tmp_path):
    r = _repo(tmp_path)
    _stage(r, "a.py", "x\n")
    fake(Verdict(holds=False, confidence=0.97, reason="README still documents the old flag"))
    out = make_sure_that(True, _hx(), _scope(r, ["a.py"]), staged_diff(r), SETTINGS)
    assert len(out) == 1
    assert "README still documents the old flag" in out[0]
    assert "97%" in out[0]
    assert not isinstance(out[0], Advisory)


def test_failure_with_low_confidence_is_advisory(fake, tmp_path):
    r = _repo(tmp_path)
    _stage(r, "a.py", "x\n")
    fake(Verdict(holds=False, confidence=0.55, reason="unsure"))
    out = make_sure_that(True, _hx(), _scope(r, ["a.py"]), staged_diff(r), SETTINGS)
    assert len(out) == 1 and isinstance(out[0], Advisory)
    assert "55%" in out[0]


def test_failure_without_confidence_is_taken_at_face_value(fake, tmp_path):
    r = _repo(tmp_path)
    _stage(r, "a.py", "x\n")
    fake(Verdict(holds=False, confidence=None, reason="nope"))
    out = make_sure_that(True, _hx(), _scope(r, ["a.py"]), staged_diff(r), SETTINGS)
    assert len(out) == 1 and not isinstance(out[0], Advisory)


def test_failure_below_warn_above_is_suppressed(fake, tmp_path):
    r = _repo(tmp_path)
    _stage(r, "a.py", "x\n")
    fake(Verdict(holds=False, confidence=0.3, reason="meh"))
    settings = {"judge": {"warn_above": 0.5}}
    out = make_sure_that(True, _hx(), _scope(r, ["a.py"], settings=settings), staged_diff(r), settings)
    assert out is None


def test_judge_error_fails_open_as_advisory(fake, tmp_path):
    r = _repo(tmp_path)
    _stage(r, "a.py", "x\n")
    fake(Verdict(holds=None, error="judge at http://fake/v1 unreachable: refused"))
    out = make_sure_that(True, _hx(), _scope(r, ["a.py"]), staged_diff(r), SETTINGS)
    assert len(out) == 1 and isinstance(out[0], Advisory)
    assert "unreachable" in out[0] and "could not be judged" in out[0]


def test_no_judge_configured_is_an_advisory_not_a_block(tmp_path):
    r = _repo(tmp_path)
    _stage(r, "a.py", "x\n")
    out = make_sure_that(True, _hx(), _scope(r, ["a.py"], settings={}), staged_diff(r), {})
    assert len(out) == 1 and isinstance(out[0], Advisory)
    assert "settings" in out[0] and "judge" in out[0]


def test_verdicts_are_cached_per_evidence(fake, tmp_path):
    r = _repo(tmp_path)
    _stage(r, "a.py", "x\n")
    j = fake(Verdict(holds=False, confidence=0.9, reason="first"))
    args = (True, _hx(), _scope(r, ["a.py"]), staged_diff(r), SETTINGS)
    first = make_sure_that(*args)
    second = make_sure_that(*args)
    assert first == second and len(j.calls) == 1
    _stage(r, "a.py", "y\n")  # evidence changed → asked again
    make_sure_that(True, _hx(), _scope(r, ["a.py"]), staged_diff(r), SETTINGS)
    assert len(j.calls) == 2


# --- @file references ---------------------------------------------------------


def test_find_references_parses_at_paths():
    from henxels.statements.builtins.judgement import find_references

    assert find_references("None of the words in @banned-words.md are used.") == ["banned-words.md"]
    assert find_references("see @docs/style.md and @./glossary.md, please") == ["docs/style.md", "glossary.md"]
    assert find_references('follows @"my notes/tone guide.md".') == ["my notes/tone guide.md"]
    assert find_references("mail me@example.com about @x.md") == ["x.md"]  # an email is not a reference
    assert find_references("no refs here") == []


def test_referenced_file_content_reaches_the_judge(fake, tmp_path):
    r = _repo(tmp_path)
    _commit(r, "banned-words.md", "- synergy\n- leverage\n")
    _stage(r, "post.md", "We leverage synergy.\n")
    j = fake(Verdict(holds=False, confidence=0.99, reason="uses 'leverage' and 'synergy'"))
    hx = _hx(text="None of the words in @banned-words.md are used")
    out = make_sure_that(True, hx, _scope(r, ["post.md"], locations=["./post.md"]), staged_diff(r), SETTINGS)
    assert len(out) == 1 and "leverage" in out[0]
    sentence, why, evidence, references = j.calls[0]
    assert references == {"banned-words.md": "- synergy\n- leverage\n"}
    assert sentence == "None of the words in @banned-words.md are used"  # the sentence is left as written


def test_references_in_why_are_resolved_too(fake, tmp_path):
    r = _repo(tmp_path)
    _commit(r, "tone.md", "be kind\n")
    _stage(r, "post.md", "x\n")
    j = fake()
    make_sure_that(True, _hx(why="tone is defined in @tone.md"), _scope(r, ["post.md"], locations=["./post.md"]), staged_diff(r), SETTINGS)
    assert j.calls[0][3] == {"tone.md": "be kind\n"}


def test_reference_reads_the_staged_version_when_the_list_itself_is_staged(fake, tmp_path):
    r = _repo(tmp_path)
    _commit(r, "banned-words.md", "- old\n")
    _stage(r, "banned-words.md", "- new\n")
    _stage(r, "post.md", "x\n")
    j = fake()
    make_sure_that(True, _hx(text="none of @banned-words.md"), _scope(r, ["post.md"], locations=["./post.md"]), staged_diff(r), SETTINGS)
    assert j.calls[0][3]["banned-words.md"] == "- new\n"


def test_missing_reference_fails_open_as_advisory(fake, tmp_path):
    r = _repo(tmp_path)
    _stage(r, "post.md", "x\n")
    j = fake()
    out = make_sure_that(True, _hx(text="none of @nope.md"), _scope(r, ["post.md"]), staged_diff(r), SETTINGS)
    assert len(out) == 1 and isinstance(out[0], Advisory)
    assert "@nope.md" in out[0] and "not found" in out[0]
    assert j.calls == []  # nothing sent


def test_reference_escaping_the_repo_is_refused(fake, tmp_path):
    r = _repo(tmp_path)
    (tmp_path.parent / "outside.md").write_text("secret\n")
    _stage(r, "post.md", "x\n")
    j = fake()
    out = make_sure_that(True, _hx(text="none of @../outside.md"), _scope(r, ["post.md"]), staged_diff(r), SETTINGS)
    assert len(out) == 1 and isinstance(out[0], Advisory)
    assert "outside the repository" in out[0]
    assert j.calls == []


def test_changing_the_referenced_file_invalidates_the_cache(fake, tmp_path):
    r = _repo(tmp_path)
    _commit(r, "banned-words.md", "- a\n")
    _stage(r, "post.md", "x\n")
    j = fake(Verdict(holds=True, reason="ok"), Verdict(holds=True, reason="ok"))
    hx = _hx(text="none of @banned-words.md")
    scope = _scope(r, ["post.md"], locations=["./post.md"])
    make_sure_that(True, hx, scope, staged_diff(r), SETTINGS)
    make_sure_that(True, hx, scope, staged_diff(r), SETTINGS)
    assert len(j.calls) == 1  # cached
    _stage(r, "banned-words.md", "- a\n- b\n")
    make_sure_that(True, hx, scope, staged_diff(r), SETTINGS)
    assert len(j.calls) == 2  # the list changed → asked again


# --- through the runner: confidence demotes block → warn ----------------------


def test_runner_demotes_low_confidence_block_to_warn(fake, tmp_path):
    r = _repo(tmp_path)
    _stage(r, "a.py", "x\n")
    fake(Verdict(holds=False, confidence=0.6, reason="unsure"))
    c = Contract(settings=SETTINGS, henxels=[_hx(level="block")])
    findings = run_contract(c, r, ["a.py"], diff=staged_diff(r))
    assert len(findings) == 1 and findings[0].level == WARN
    assert findings[0].henxel == "Behaviour changes are described in the docs"


def test_runner_keeps_block_when_confident(fake, tmp_path):
    r = _repo(tmp_path)
    _stage(r, "a.py", "x\n")
    fake(Verdict(holds=False, confidence=0.95, reason="sure"))
    c = Contract(settings=SETTINGS, henxels=[_hx(level="block")])
    findings = run_contract(c, r, ["a.py"], diff=staged_diff(r))
    assert findings[0].is_block
