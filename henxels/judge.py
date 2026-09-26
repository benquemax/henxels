"""The judge: ask a language model whether a natural-language statement holds.

Some henxels can't be reduced to a glob or a regex — "behaviour changes are described
in the docs", "the journal entry says what was decided, not just what was done". Those
are written as a plain sentence (``make_sure_that:``) and handed, together with the
staged changes in scope, to a *judge*: any OpenAI-compatible chat endpoint (Ollama,
llama.cpp, vLLM, LM Studio, OpenAI, OpenRouter, …), local or remote, with or without
an API key. Standard library only — one ``urllib`` POST.

The judge answers with a verdict: ``holds`` (bool), a ``reason`` (the instruction an
agent can act on), and — when the endpoint returns logprobs — a calibrated
``confidence`` in [0, 1] read from the probability mass on the decision token. That
number is what lets a contract say "block only when the judge is sure".

Failure to reach or parse the judge is **never** a verdict: ``holds`` is None and
``error`` says why. A pre-commit hook must not lock a repo because an API is down.
"""

from __future__ import annotations

import json
import math
import os
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field

DEFAULT_BASE_URL = "http://localhost:11434/v1"  # Ollama's OpenAI-compatible endpoint
DEFAULT_MODEL = "qwen3:8b"
DEFAULT_API_KEY_ENV = "OPENAI_API_KEY"
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_CHARS = 60_000  # ~15k tokens of evidence; beyond that the diff is truncated
DEFAULT_BLOCK_ABOVE = 0.8  # a `level: block` henxel blocks only when confidence >= this
DEFAULT_WARN_ABOVE = 0.0  # below block_above (or without confidence) a failure is a warning

SYSTEM_PROMPT = (
    "You are a strict, literal reviewer of a code repository. You are given one "
    "statement from the repository's contract and the staged changes it governs. "
    "Decide whether the statement HOLDS for these changes. Judge only what the "
    "changes show; do not assume work happened elsewhere. If the changes are "
    "irrelevant to the statement, it holds.\n"
    'Reply with a single JSON object and nothing else, in exactly this shape: '
    '{"holds": true|false, "reason": "<one or two sentences: if it does not hold, '
    'say precisely what to change; if it holds, say why briefly>"}. '
    'The "holds" key must come first.'
)

Transport = Callable[[str, dict, bytes, float], bytes]


@dataclass(frozen=True)
class JudgeConfig:
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    api_key: str | None = None
    timeout: float = DEFAULT_TIMEOUT
    max_chars: int = DEFAULT_MAX_CHARS
    extra_body: dict = field(default_factory=dict)
    block_above: float = DEFAULT_BLOCK_ABOVE
    warn_above: float = DEFAULT_WARN_ABOVE
    fallbacks: tuple[JudgeConfig, ...] = ()


@dataclass(frozen=True)
class Verdict:
    holds: bool | None  # None = the judge could not be consulted (see error)
    confidence: float | None = None  # P(the given answer) in [0, 1], when logprobs are available
    reason: str | None = None
    error: str | None = None
    model: str | None = None  # which model answered (set when a fallback was used)
    base_url: str | None = None  # which endpoint answered (set when a fallback was used)


# Where the judge lives is a fact about a machine, not a rule of the project, so these
# override the committed contract. The contract only decides *that* there is a judge.
ENV_URL = "HENXELS_JUDGE_URL"
ENV_MODEL = "HENXELS_JUDGE_MODEL"
ENV_TIMEOUT = "HENXELS_JUDGE_TIMEOUT"
ENV_EXTRA_BODY = "HENXELS_JUDGE_EXTRA_BODY"  # JSON, merged over the contract's extra_body
ENV_FALLBACKS = "HENXELS_JUDGE_FALLBACKS"  # JSON array of fallback judge configs, appended to the contract's


def _parse_one_judge(raw: dict) -> JudgeConfig:
    """Parse a single judge config dict (used for both primary and fallback entries)."""
    key_env = str(raw.get("api_key_env", DEFAULT_API_KEY_ENV))
    key = os.environ.get(key_env) or None
    extra_body = dict(raw.get("extra_body") or {})
    return JudgeConfig(
        base_url=str(raw.get("base_url", DEFAULT_BASE_URL)).rstrip("/"),
        model=str(raw.get("model", DEFAULT_MODEL)),
        api_key=key,
        timeout=float(raw.get("timeout", DEFAULT_TIMEOUT)),
        max_chars=int(raw.get("max_chars", DEFAULT_MAX_CHARS)),
        extra_body=extra_body,
        block_above=float(raw.get("block_above", DEFAULT_BLOCK_ABOVE)),
        warn_above=float(raw.get("warn_above", DEFAULT_WARN_ABOVE)),
    )


def config_from_settings(settings: dict) -> JudgeConfig | None:
    """Read ``settings.judge`` (``true`` for defaults, or a mapping). None = judging is off.

    ``HENXELS_JUDGE_URL`` / ``_MODEL`` / ``_TIMEOUT`` / ``_EXTRA_BODY`` in the environment
    win over the contract, so a LAN endpoint never needs to be committed.
    ``HENXELS_JUDGE_FALLBACKS`` (JSON array) appends fallback judges to the contract's list.
    """
    raw = (settings or {}).get("judge")
    if not raw:
        return None
    raw = raw if isinstance(raw, dict) else {}
    env = os.environ
    extra_body = dict(raw.get("extra_body") or {})
    if env.get(ENV_EXTRA_BODY):
        try:
            extra_body.update(json.loads(env[ENV_EXTRA_BODY]))
        except (ValueError, TypeError, AttributeError):
            pass  # a typo in the shell profile must not break every commit
    # Parse fallbacks from YAML
    fallbacks_raw = raw.get("fallbacks") or []
    fallbacks = tuple(_parse_one_judge(fb) for fb in fallbacks_raw if isinstance(fb, dict))
    # Append env fallbacks
    if env.get(ENV_FALLBACKS):
        try:
            env_fbs = json.loads(env[ENV_FALLBACKS])
            if isinstance(env_fbs, list):
                fallbacks += tuple(_parse_one_judge(fb) for fb in env_fbs if isinstance(fb, dict))
        except (ValueError, TypeError, AttributeError):
            pass  # bad JSON in env must not break commits
    key_env = str(raw.get("api_key_env", DEFAULT_API_KEY_ENV))
    key = os.environ.get(key_env) or None
    return JudgeConfig(
        base_url=str(env.get(ENV_URL) or raw.get("base_url", DEFAULT_BASE_URL)).rstrip("/"),
        model=str(env.get(ENV_MODEL) or raw.get("model", DEFAULT_MODEL)),
        api_key=key,
        timeout=float(env.get(ENV_TIMEOUT) or raw.get("timeout", DEFAULT_TIMEOUT)),
        max_chars=int(raw.get("max_chars", DEFAULT_MAX_CHARS)),
        extra_body=extra_body,
        block_above=float(raw.get("block_above", DEFAULT_BLOCK_ABOVE)),
        warn_above=float(raw.get("warn_above", DEFAULT_WARN_ABOVE)),
        fallbacks=fallbacks,
    )


# --- transport ---------------------------------------------------------------


def _urllib_transport(url: str, headers: dict, body: bytes, timeout: float) -> bytes:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - user-configured endpoint
        return resp.read()


class OpenAICompatibleJudge:
    """POST /chat/completions on any OpenAI-compatible server; parse a JSON verdict.

    When the primary endpoint fails (transport error, bad response), fallback judges
    are tried in order. A real verdict (holds=True or False) from any endpoint stops
    the chain — only infrastructure failures trigger fallback.
    """

    def __init__(self, config: JudgeConfig, transport: Transport | None = None):
        self.config = config
        self.transport = transport or _urllib_transport
        # Test hook: override transports per base_url for deterministic fallback testing
        self._transports: dict[str, Transport] | None = None

    def _transport_for(self, base_url: str) -> Transport:
        if self._transports and base_url in self._transports:
            return self._transports[base_url]
        return self.transport

    def _try_one(
        self, cfg: JudgeConfig, sentence: str, why: str, evidence: str, references: dict[str, str]
    ) -> Verdict:
        """Try a single endpoint. Returns a Verdict — holds=None means it failed."""
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if cfg.api_key:
            headers["Authorization"] = f"Bearer {cfg.api_key}"
        body = {
            "model": cfg.model,
            "temperature": 0,
            "max_tokens": 800,  # room for a reason; thinking models spend budget before the JSON
            "logprobs": True,
            "top_logprobs": 5,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _user_prompt(sentence, why, evidence, cfg.max_chars, references)},
            ],
        }
        body.update(cfg.extra_body)
        transport = self._transport_for(cfg.base_url)
        try:
            raw = transport(f"{cfg.base_url}/chat/completions", headers, json.dumps(body).encode(), cfg.timeout)
        except urllib.error.HTTPError as exc:
            return Verdict(holds=None, error=f"judge at {cfg.base_url} answered HTTP {exc.code}")
        except Exception as exc:  # noqa: BLE001 - any transport failure fails open
            return Verdict(holds=None, error=f"judge at {cfg.base_url} unreachable: {exc}")
        try:
            data = json.loads(raw.decode("utf-8", errors="replace"))
        except ValueError:
            return Verdict(holds=None, error=f"judge at {cfg.base_url} returned a non-JSON response")
        if not isinstance(data, dict):
            return Verdict(holds=None, error=f"judge at {cfg.base_url} returned an unexpected payload")
        if "error" in data and "choices" not in data:
            msg = data["error"].get("message") if isinstance(data["error"], dict) else data["error"]
            return Verdict(holds=None, error=f"judge at {cfg.base_url} refused: {msg}")
        return parse_response(data)

    def judge(self, sentence: str, why: str, evidence: str, references: dict[str, str] | None = None) -> Verdict:
        """``references`` maps ``@path`` names used in the sentence to their content.

        Tries the primary endpoint first, then each fallback in order. Only transport/
        API failures trigger fallback — a real verdict (even 'does not hold') stops the chain.
        """
        refs = references or {}
        v = self._try_one(self.config, sentence, why, evidence, refs)
        if v.holds is not None:
            return v  # primary gave a real answer
        last_error = v.error
        for fb_cfg in self.config.fallbacks:
            v = self._try_one(fb_cfg, sentence, why, evidence, refs)
            if v.holds is not None:
                # Tag the verdict with which fallback answered
                return Verdict(
                    holds=v.holds, confidence=v.confidence, reason=v.reason,
                    model=fb_cfg.model, base_url=fb_cfg.base_url,
                )
            last_error = v.error
        # All endpoints failed
        return Verdict(holds=None, error=last_error)


def _user_prompt(sentence: str, why: str, evidence: str, max_chars: int, references: dict[str, str]) -> str:
    parts = [f"Statement: {sentence.strip()}"]
    if why.strip():
        parts.append(f"Background (why this rule exists): {why.strip()}")
    budget = max_chars
    if references:
        # Referenced files come first and are protected: a rule's list is small and
        # load-bearing, so it's the diff that gets cut when the budget runs out.
        blocks = []
        for name, text in references.items():
            blocks.append(f"@{name} in the statement refers to the file below.\n--- {name} ---\n{text.rstrip()}\n--- end of {name} ---")
        refs = "\n\n".join(blocks)
        parts.append(f"Referenced files:\n\n{refs}")
        budget = max(1000, max_chars - len(refs))
    if len(evidence) > budget:
        evidence = evidence[:budget] + f"\n\n[... truncated: {len(evidence) - budget} more characters not shown]"
    parts.append(f"Staged changes in scope:\n\n{evidence}")
    return "\n\n".join(parts)


# --- parsing -------------------------------------------------------------------

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
_HOLDS = re.compile(r'"holds"\s*:\s*(true|false)', re.IGNORECASE)


def parse_response(data: dict) -> Verdict:
    """Turn a chat-completions payload into a Verdict (holds/confidence/reason)."""
    try:
        choice = data["choices"][0]
        message = choice["message"]
        content = message.get("content") or ""
    except (KeyError, IndexError, TypeError, AttributeError):
        return Verdict(holds=None, error="unparseable judge response: no choices")
    holds, reason = _extract_decision(content)
    if holds is None:  # a thinking model may have spent its budget: salvage from the trace
        holds, reason = _extract_decision(str(message.get("reasoning_content") or ""))
    if holds is None:
        return Verdict(holds=None, error=f"unparseable judge response: {content.strip()[:120]!r}")
    confidence = _confidence(choice.get("logprobs"), holds)
    return Verdict(holds=holds, confidence=confidence, reason=reason)


def _extract_decision(content: str) -> tuple[bool | None, str | None]:
    text = _THINK.sub("", content).strip()
    fenced = _FENCE.search(text)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            if isinstance(obj, dict) and isinstance(obj.get("holds"), bool):
                reason = obj.get("reason")
                return obj["holds"], (str(reason).strip() if reason else None)
        except ValueError:
            pass
    m = _HOLDS.search(text)  # model got the shape slightly wrong; salvage the decision
    if m:
        return m.group(1).lower() == "true", None
    return None, None


def _confidence(logprobs, holds: bool) -> float | None:
    """P(the given answer) from the decision token's distribution, or None."""
    tokens = (logprobs or {}).get("content") if isinstance(logprobs, dict) else None
    if not tokens:
        return None
    seen = ""
    for tok in tokens:
        text = str(tok.get("token", ""))
        seen += text
        if "holds" not in seen:
            continue
        word = text.strip().strip('"\'').lower()
        if word not in ("true", "false"):
            continue
        p_true = p_false = 0.0
        for alt in tok.get("top_logprobs") or []:
            w = str(alt.get("token", "")).strip().strip('"\'').lower()
            if w == "true":
                p_true += math.exp(alt["logprob"])
            elif w == "false":
                p_false += math.exp(alt["logprob"])
        chosen, other = (p_true, p_false) if holds else (p_false, p_true)
        if chosen == 0.0:  # the chosen token wasn't in top_logprobs: use its own logprob
            chosen = math.exp(tok.get("logprob", 0.0))
        return max(0.0, min(1.0, chosen / (chosen + other) if other else chosen))
    return None
