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


# --- fallback judges --------------------------------------------------------


def test_fallback_judge_is_used_when_primary_fails(monkeypatch, tmp_path):
    """When the primary transport fails, the fallback is tried and its verdict is used."""
    r = _repo(tmp_path)
    _stage(r, "a.py", "x\n")
    settings = {
        "judge": {
            "base_url": "http://primary/v1",
            "model": "primary-m",
            "fallbacks": [{"base_url": "http://backup/v1", "model": "backup-m"}],
        }
    }
    from henxels.judge import OpenAICompatibleJudge

    tried = []

    class TrackingTransport:
        """Routes requests to different fake responses based on URL."""
        def __call__(self, url, headers, body, timeout):
            tried.append(url)
            if "primary" in url:
                raise OSError("primary down")
            import json as _json
            return _json.dumps({"choices": [{"message": {"content": '{"holds": true, "reason": "backup ok"}'}}]}).encode()

    monkeypatch.setattr(judgement, "OpenAICompatibleJudge", lambda cfg: OpenAICompatibleJudge(cfg, transport=TrackingTransport()))
    out = make_sure_that(True, _hx(), _scope(r, ["a.py"], settings=settings), staged_diff(r), settings)
    assert out is None  # backup said holds=True → no finding
    assert any("primary" in u for u in tried)
    assert any("backup" in u for u in tried)


def test_all_judges_failing_mentions_last_error(monkeypatch, tmp_path):
    """When primary and all fallbacks fail, the advisory mentions the last error."""
    r = _repo(tmp_path)
    _stage(r, "a.py", "x\n")
    settings = {
        "judge": {
            "base_url": "http://primary/v1",
            "model": "primary-m",
            "fallbacks": [{"base_url": "http://backup/v1", "model": "backup-m"}],
        }
    }
    from henxels.judge import OpenAICompatibleJudge

    class FailAllTransport:
        def __call__(self, url, headers, body, timeout):
            raise OSError(f"{url} unreachable")

    monkeypatch.setattr(judgement, "OpenAICompatibleJudge", lambda cfg: OpenAICompatibleJudge(cfg, transport=FailAllTransport()))
    out = make_sure_that(True, _hx(), _scope(r, ["a.py"], settings=settings), staged_diff(r), settings)
    assert len(out) == 1 and isinstance(out[0], Advisory)
    assert "could not be judged" in out[0]


# --- evidence mode (full content vs diff-only) ------------------------------


def test_evidence_full_sends_file_contents_not_diffs(fake, tmp_path):
    """evidence: full sends the complete file contents of all scope files, not diffs."""
    r = _repo(tmp_path)
    _commit(r, "a.py", "original content\n")
    _stage(r, "a.py", "modified content\n")
    j = fake(Verdict(holds=True, reason="ok"))
    param = {"text": "all files follow convention X", "evidence": "full"}
    out = make_sure_that(param, _hx(), _scope(r, ["a.py"]), staged_diff(r), SETTINGS)
    assert out is None
    sentence, why, evidence, _ = j.calls[0]
    assert sentence == "all files follow convention X"
    # Full evidence contains the file content, not a diff
    assert "modified content" in evidence
    assert "--- a/a.py" not in evidence  # no unified diff headers


def test_evidence_full_includes_unchanged_files(fake, tmp_path):
    """evidence: full includes files in scope even when they have no staged changes."""
    r = _repo(tmp_path)
    _commit(r, "a.py", "chapter one\n")
    _commit(r, "b.py", "chapter two\n")
    _stage(r, "a.py", "chapter one revised\n")  # only a.py changed
    j = fake(Verdict(holds=True, reason="ok"))
    param = {"text": "all chapters are consistent", "evidence": "full"}
    # Both files are in scope, but only a.py has changes
    out = make_sure_that(param, _hx(), _scope(r, ["a.py", "b.py"]), staged_diff(r), SETTINGS)
    assert out is None
    _, _, evidence, _ = j.calls[0]
    assert "chapter one revised" in evidence  # changed file
    assert "chapter two" in evidence  # unchanged file still included


def test_evidence_full_works_without_diff(fake, tmp_path):
    """evidence: full works even when diff is None (corpus gate, not diff gate)."""
    r = _repo(tmp_path)
    _commit(r, "a.py", "content\n")
    j = fake(Verdict(holds=True, reason="ok"))
    param = {"text": "all files are valid", "evidence": "full"}
    out = make_sure_that(param, _hx(), _scope(r, ["a.py"]), None, SETTINGS)
    assert out is None
    assert len(j.calls) == 1
    _, _, evidence, _ = j.calls[0]
    assert "content" in evidence


def test_evidence_default_is_diff(fake, tmp_path):
    """Without evidence key, behavior is unchanged: diff-only, skips when no changes."""
    r = _repo(tmp_path)
    _commit(r, "a.py", "content\n")
    j = fake()
    # No staged changes → diff exists but evidence is empty → passes silently
    out = make_sure_that(True, _hx(), _scope(r, ["a.py"]), staged_diff(r), SETTINGS)
    assert out is None
    assert j.calls == []  # no tokens spent


def test_evidence_full_with_sentences_list(fake, tmp_path):
    """evidence: full works with a list of sentences."""
    r = _repo(tmp_path)
    _commit(r, "a.py", "content\n")
    j = fake(Verdict(holds=True, reason="ok"), Verdict(holds=True, reason="ok"))
    param = {"sentences": ["rule one", "rule two"], "evidence": "full"}
    out = make_sure_that(param, _hx(), _scope(r, ["a.py"]), None, SETTINGS)
    assert out is None
    assert [c[0] for c in j.calls] == ["rule one", "rule two"]


def test_evidence_full_is_truncated_at_prompt_level(fake, tmp_path):
    """Full evidence can be large; the judge's max_chars budget truncates the prompt."""
    r = _repo(tmp_path)
    _commit(r, "big.py", "x" * 100_000 + "\n")
    j = fake(Verdict(holds=True, reason="ok"))
    param = {"text": "file is valid", "evidence": "full"}
    settings = {"judge": {"base_url": "http://fake/v1", "model": "m", "max_chars": 5000}}
    out = make_sure_that(param, _hx(), _scope(r, ["big.py"]), None, settings)
    assert out is None
    # The evidence passed to the judge is the raw full content; truncation happens
    # inside the judge's prompt builder (_user_prompt), not at the evidence level.
    _, _, evidence, _ = j.calls[0]
    assert "x" * 100_000 in evidence  # full content reaches the judge object


def test_build_full_evidence_includes_all_scope_files(tmp_path):
    """build_full_evidence returns content of every file in scope."""
    from henxels.statements.builtins.judgement import build_full_evidence
    r = _repo(tmp_path)
    _commit(r, "a.py", "alpha\n")
    _commit(r, "b.py", "beta\n")
    scope = _scope(r, ["a.py", "b.py"])
    ev = build_full_evidence(scope.files, scope)
    assert "alpha" in ev and "beta" in ev
    assert "a.py" in ev and "b.py" in ev  # filenames visible


# --- evidence chunking ------------------------------------------------------


def test_chunk_evidence_splits_on_file_boundaries():
    """Chunks never split mid-file; each file's block is atomic."""
    from henxels.statements.builtins.judgement import chunk_evidence
    blocks = [
        "--- a.py ---\n" + "a" * 3000 + "\n--- end ---",
        "--- b.py ---\n" + "b" * 3000 + "\n--- end ---",
        "--- c.py ---\n" + "c" * 3000 + "\n--- end ---",
    ]
    chunks = chunk_evidence(blocks, max_chars=7000)
    assert len(chunks) == 2  # first two fit in one chunk, third in another
    assert "a.py" in chunks[0] and "b.py" in chunks[0]
    assert "c.py" in chunks[1]


def test_chunk_evidence_single_oversized_file_is_its_own_chunk():
    """A file larger than max_chars is sent alone — can't split further."""
    from henxels.statements.builtins.judgement import chunk_evidence
    blocks = [
        "--- big.py ---\n" + "x" * 100_000 + "\n--- end ---",
        "--- small.py ---\n" + "y" * 100 + "\n--- end ---",
    ]
    chunks = chunk_evidence(blocks, max_chars=60_000)
    assert len(chunks) == 2
    assert "big.py" in chunks[0]
    assert "small.py" in chunks[1]


def test_chunk_evidence_under_budget_is_one_chunk():
    """When everything fits, no splitting happens."""
    from henxels.statements.builtins.judgement import chunk_evidence
    blocks = ["--- a.py ---\nshort\n--- end ---"]
    chunks = chunk_evidence(blocks, max_chars=60_000)
    assert len(chunks) == 1
    assert chunks[0] == blocks[0]


def test_chunked_judging_sends_multiple_requests(fake, tmp_path):
    """When evidence exceeds max_chars, the judge is called once per chunk."""
    r = _repo(tmp_path)
    # Create several files that together exceed the budget
    for i in range(5):
        _stage(r, f"file{i}.py", f"content_{i}\n" * 500)
    j = fake(*[Verdict(holds=True, reason="ok")] * 5)
    settings = {"judge": {"base_url": "http://fake/v1", "model": "m", "max_chars": 2000}}
    out = make_sure_that(True, _hx(), _scope(r, [f"file{i}.py" for i in range(5)]), staged_diff(r), settings)
    assert out is None  # all chunks said holds
    assert len(j.calls) > 1  # multiple requests were made


def test_chunked_judging_fails_if_any_chunk_fails(fake, tmp_path):
    """If any chunk says 'does not hold', the overall result fails."""
    r = _repo(tmp_path)
    for i in range(4):
        _stage(r, f"file{i}.py", f"content_{i}\n" * 500)
    # First chunk passes, second chunk fails
    fake(
        Verdict(holds=True, reason="ok"),
        Verdict(holds=False, confidence=0.95, reason="file2 violates the rule"),
    )
    settings = {"judge": {"base_url": "http://fake/v1", "model": "m", "max_chars": 2000}}
    out = make_sure_that(True, _hx(), _scope(r, [f"file{i}.py" for i in range(4)]), staged_diff(r), settings)
    assert out is not None
    assert any("violates" in str(o) for o in out)


def test_chunked_judging_caches_per_chunk(fake, tmp_path):
    """Each chunk is cached independently; re-run only asks for changed chunks."""
    r = _repo(tmp_path)
    for i in range(4):
        _stage(r, f"file{i}.py", f"content_{i}\n" * 500)
    j = fake(*[Verdict(holds=True, reason="ok")] * 4)
    settings = {"judge": {"base_url": "http://fake/v1", "model": "m", "max_chars": 2000}}
    args = (True, _hx(), _scope(r, [f"file{i}.py" for i in range(4)]), staged_diff(r), settings)
    make_sure_that(*args)
    first_calls = len(j.calls)
    assert first_calls > 1
    make_sure_that(*args)
    assert len(j.calls) == first_calls  # all cached, no new calls
