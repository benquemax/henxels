"""The judge: an OpenAI-compatible chat endpoint asked whether a statement holds.

Everything here runs against a fake transport — no network. The live journey is an
opt-in e2e (HENXELS_JUDGE_URL) in tests/e2e.
"""

from __future__ import annotations

import json
import math

import pytest

from henxels import judge as judge_mod
from henxels.judge import (
    JudgeConfig,
    OpenAICompatibleJudge,
    Verdict,
    config_from_settings,
    parse_response,
)

# --- config ---------------------------------------------------------------


def test_config_defaults_to_local_ollama_and_no_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = config_from_settings({})
    assert cfg is None  # judging is opt-in: no `judge:` block → no judge


def test_config_reads_settings_and_key_from_env(monkeypatch):
    monkeypatch.setenv("MY_KEY", "sk-test")
    cfg = config_from_settings(
        {"judge": {"base_url": "http://localhost:11434/v1/", "model": "qwen3:8b", "api_key_env": "MY_KEY"}}
    )
    assert cfg.base_url == "http://localhost:11434/v1"  # trailing slash stripped
    assert cfg.model == "qwen3:8b"
    assert cfg.api_key == "sk-test"
    assert cfg.timeout > 0
    assert cfg.max_chars > 0


def test_env_overrides_where_the_judge_lives(monkeypatch):
    """The contract says *that* there is a judge; the machine says *where*. Hostnames
    and model ids are infrastructure, not rules — they don't belong in a committed file."""
    monkeypatch.setenv("HENXELS_JUDGE_URL", "http://lan-box:4800/v1/")
    monkeypatch.setenv("HENXELS_JUDGE_MODEL", "big-model")
    monkeypatch.setenv("HENXELS_JUDGE_EXTRA_BODY", '{"enable_thinking": false}')
    monkeypatch.setenv("HENXELS_JUDGE_TIMEOUT", "300")
    cfg = config_from_settings({"judge": {"base_url": "http://committed:1/v1", "model": "small", "timeout": 5}})
    assert cfg.base_url == "http://lan-box:4800/v1"
    assert cfg.model == "big-model"
    assert cfg.extra_body == {"enable_thinking": False}
    assert cfg.timeout == 300.0


def test_env_extra_body_merges_over_the_contracts(monkeypatch):
    monkeypatch.setenv("HENXELS_JUDGE_EXTRA_BODY", '{"b": 2}')
    cfg = config_from_settings({"judge": {"extra_body": {"a": 1, "b": 1}}})
    assert cfg.extra_body == {"a": 1, "b": 2}


def test_env_does_not_switch_judging_on(monkeypatch):
    monkeypatch.setenv("HENXELS_JUDGE_URL", "http://lan-box:4800/v1")
    assert config_from_settings({}) is None  # no judge: in the contract → no judge


def test_bad_env_extra_body_is_ignored_not_fatal(monkeypatch):
    monkeypatch.setenv("HENXELS_JUDGE_EXTRA_BODY", "{not json")
    assert config_from_settings({"judge": True}).extra_body == {}


def test_config_true_means_defaults(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = config_from_settings({"judge": True})
    assert cfg.base_url == judge_mod.DEFAULT_BASE_URL
    assert cfg.model == judge_mod.DEFAULT_MODEL
    assert cfg.api_key is None


def test_config_missing_key_env_is_not_an_error(monkeypatch):
    monkeypatch.delenv("NOPE_KEY", raising=False)
    cfg = config_from_settings({"judge": {"api_key_env": "NOPE_KEY"}})
    assert cfg.api_key is None


def test_config_extra_body_and_thresholds():
    cfg = config_from_settings(
        {"judge": {"extra_body": {"chat_template_kwargs": {"enable_thinking": False}}, "block_above": 0.9, "warn_above": 0.5}}
    )
    assert cfg.extra_body == {"chat_template_kwargs": {"enable_thinking": False}}
    assert cfg.block_above == 0.9
    assert cfg.warn_above == 0.5


# --- response parsing -------------------------------------------------------


def _resp(content, logprobs=None):
    choice = {"message": {"content": content}}
    if logprobs is not None:
        choice["logprobs"] = {"content": logprobs}
    return {"choices": [choice]}


def test_parse_plain_json():
    v = parse_response(_resp('{"holds": false, "reason": "docs untouched"}'))
    assert v == Verdict(holds=False, confidence=None, reason="docs untouched")


def test_parse_json_in_code_fence_and_prose():
    v = parse_response(_resp('Sure!\n```json\n{"holds": true, "reason": "ok"}\n```\n'))
    assert v.holds is True and v.reason == "ok"


def test_parse_tolerates_think_block():
    v = parse_response(_resp('<think>hmm</think>{"holds": true, "reason": "fine"}'))
    assert v.holds is True


def test_parse_salvages_decision_from_reasoning_content():
    data = {"choices": [{"message": {"content": "", "reasoning_content": 'so the answer is {"holds": false, "reason": "r"}'}}]}
    v = parse_response(data)
    assert v.holds is False and v.reason == "r"


def test_parse_garbage_is_an_error_not_a_verdict():
    v = parse_response(_resp("I cannot answer that."))
    assert v.holds is None
    assert "unparseable" in v.error


def test_parse_confidence_from_logprob_of_holds_token():
    # The token right after `"holds": ` carries the decision; its top_logprobs give P(true) vs P(false).
    lp = [
        {"token": '{"', "logprob": -0.01, "top_logprobs": []},
        {"token": "holds", "logprob": -0.01, "top_logprobs": []},
        {"token": '":', "logprob": -0.01, "top_logprobs": []},
        {"token": " false", "logprob": math.log(0.8), "top_logprobs": [
            {"token": " false", "logprob": math.log(0.8)},
            {"token": " true", "logprob": math.log(0.2)},
        ]},
        {"token": ',', "logprob": -0.01, "top_logprobs": []},
    ]
    v = parse_response(_resp('{"holds": false, "reason": "x"}', lp))
    assert v.holds is False
    assert v.confidence == pytest.approx(0.8)


def test_parse_confidence_falls_back_to_chosen_token_prob_when_alternative_missing():
    lp = [
        {"token": '{"holds":', "logprob": -0.01, "top_logprobs": []},
        {"token": " true", "logprob": math.log(0.95), "top_logprobs": [{"token": " true", "logprob": math.log(0.95)}]},
    ]
    v = parse_response(_resp('{"holds": true, "reason": "x"}', lp))
    assert v.confidence == pytest.approx(0.95)


def test_parse_no_logprobs_means_no_confidence():
    v = parse_response(_resp('{"holds": true, "reason": "x"}', logprobs=[]))
    assert v.confidence is None


# --- transport ------------------------------------------------------------


class FakeTransport:
    def __init__(self, reply=None, exc=None):
        self.reply, self.exc, self.calls = reply, exc, []

    def __call__(self, url, headers, body, timeout):
        self.calls.append((url, headers, json.loads(body), timeout))
        if self.exc:
            raise self.exc
        return json.dumps(self.reply).encode()


def _cfg(**kw):
    base = dict(base_url="http://x/v1", model="m", api_key="k", timeout=5.0, max_chars=100_000)
    base.update(kw)
    return JudgeConfig(**base)


def test_judge_posts_openai_shape_and_returns_verdict():
    t = FakeTransport(reply=_resp('{"holds": false, "reason": "missing doc"}'))
    j = OpenAICompatibleJudge(_cfg(), transport=t)
    v = j.judge("Docs are updated", "because", "diff --git a/x")
    assert v.holds is False and v.reason == "missing doc"
    url, headers, body, timeout = t.calls[0]
    assert url == "http://x/v1/chat/completions"
    assert headers["Authorization"] == "Bearer k"
    assert body["model"] == "m"
    assert body["temperature"] == 0
    assert body["logprobs"] is True
    assert body["messages"][0]["role"] == "system"
    user = body["messages"][-1]["content"]
    assert "Docs are updated" in user and "because" in user and "diff --git a/x" in user
    assert timeout == 5.0


def test_judge_without_key_sends_no_auth_header():
    t = FakeTransport(reply=_resp('{"holds": true, "reason": ""}'))
    OpenAICompatibleJudge(_cfg(api_key=None), transport=t).judge("s", "", "e")
    assert "Authorization" not in t.calls[0][1]


def test_judge_merges_extra_body():
    t = FakeTransport(reply=_resp('{"holds": true, "reason": ""}'))
    OpenAICompatibleJudge(_cfg(extra_body={"chat_template_kwargs": {"enable_thinking": False}}), transport=t).judge("s", "", "e")
    assert t.calls[0][2]["chat_template_kwargs"] == {"enable_thinking": False}


def test_judge_fails_open_on_transport_error():
    t = FakeTransport(exc=OSError("connection refused"))
    v = OpenAICompatibleJudge(_cfg(), transport=t).judge("s", "", "e")
    assert v.holds is None
    assert "connection refused" in v.error


def test_judge_fails_open_on_bad_json():
    class T:
        def __call__(self, *a, **k):
            return b"<html>502</html>"

    v = OpenAICompatibleJudge(_cfg(), transport=T()).judge("s", "", "e")
    assert v.holds is None and v.error


def test_judge_puts_referenced_files_before_the_diff():
    t = FakeTransport(reply=_resp('{"holds": true, "reason": ""}'))
    OpenAICompatibleJudge(_cfg(), transport=t).judge(
        "None of the words in @banned-words.md appear", "", "+hello", references={"banned-words.md": "- foo\n- bar\n"}
    )
    user = t.calls[0][2]["messages"][-1]["content"]
    assert "@banned-words.md" in user and "- foo" in user
    assert user.index("- foo") < user.index("+hello")  # references first, diff last
    assert "refers to the file" in user  # the model is told what @name means


def test_judge_budget_truncates_the_diff_not_the_references():
    t = FakeTransport(reply=_resp('{"holds": true, "reason": ""}'))
    OpenAICompatibleJudge(_cfg(max_chars=2000), transport=t).judge(
        "s", "", "d" * 3000, references={"list.md": "w" * 1500}
    )
    user = t.calls[0][2]["messages"][-1]["content"]
    assert "w" * 1500 in user  # the list survives intact
    assert "d" * 3000 not in user and "truncated" in user  # the diff took the cut


def test_judge_truncates_evidence_to_budget():
    t = FakeTransport(reply=_resp('{"holds": true, "reason": ""}'))
    OpenAICompatibleJudge(_cfg(max_chars=50), transport=t).judge("s", "", "x" * 500)
    user = t.calls[0][2]["messages"][-1]["content"]
    assert "x" * 500 not in user
    assert "truncated" in user
