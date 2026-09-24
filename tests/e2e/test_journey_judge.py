"""Natural-language henxels through real hooks and a real HTTP judge.

The judge is a tiny in-process OpenAI-compatible server, so the journey is hermetic yet
exercises the actual wire: the hook → henxels → POST /v1/chat/completions → verdict →
block/warn. Set HENXELS_JUDGE_URL (+ HENXELS_JUDGE_MODEL, HENXELS_JUDGE_KEY, HENXELS_JUDGE_EXTRA_BODY)
to also run the live journey against a real endpoint; raise HENXELS_E2E_TIMEOUT for a slow one.
"""

from __future__ import annotations

import json
import math
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from tests.e2e.harness import output_of

pytestmark = pytest.mark.e2e


class _FakeJudge:
    """Answers every completion with a scripted verdict; records what it was asked."""

    def __init__(self, holds: bool, p: float, reason: str):
        self.holds, self.p, self.reason, self.requests = holds, p, reason, []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):  # silence
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append((self.path, dict(self.headers), body))
                answer = json.dumps({"holds": outer.holds, "reason": outer.reason})
                token = " true" if outer.holds else " false"
                other = " false" if outer.holds else " true"
                payload = {
                    "choices": [{
                        "message": {"role": "assistant", "content": answer},
                        "logprobs": {"content": [
                            {"token": '{"holds":', "logprob": -0.001, "top_logprobs": []},
                            {"token": token, "logprob": math.log(outer.p), "top_logprobs": [
                                {"token": token, "logprob": math.log(outer.p)},
                                {"token": other, "logprob": math.log(max(1e-9, 1 - outer.p))},
                            ]},
                        ]},
                    }]
                }
                raw = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()


@pytest.fixture
def judge_factory():
    started = []

    def start(holds, p=0.95, reason="scripted"):
        j = _FakeJudge(holds, p, reason)
        started.append(j)
        return j

    yield start
    for j in started:
        j.stop()


def _contract(url: str, level: str = "block") -> str:
    return f"""settings:
  judge:
    base_url: {url}
    model: fake
    api_key_env: FAKE_JUDGE_KEY
henxels:
  - henxel: "New CLI flags are documented in README.md"
    in: [./cli.py, ./README.md]
    why: Users learn flags from the README.
    make_sure_that: true
    level: {level}
"""


def _seed(sandbox, repo, url, level="block"):
    """Seed the files before the contract exists, so the seed itself isn't judged."""
    sandbox.write(repo, "README.md", "# tool\n\n- --verbose\n")
    sandbox.write(repo, "cli.py", "def main(a):\n    pass\n")
    seeded = sandbox.commit_all(repo, "seed")
    assert seeded.returncode == 0, output_of(seeded)
    sandbox.write(repo, "henxels.yaml", _contract(url, level))
    sandbox.henxels("init", cwd=repo)
    contracted = sandbox.commit_all(repo, "contract")  # scope untouched → judge not asked
    assert contracted.returncode == 0, output_of(contracted)


def test_confident_failure_blocks_and_shows_reason(sandbox, judge_factory):
    judge = judge_factory(holds=False, p=0.96, reason="cli.py adds --json but README.md is untouched")
    repo = sandbox.repo()
    _seed(sandbox, repo, judge.url)
    judge.requests.clear()

    sandbox.write(repo, "cli.py", "def main(a):\n    if '--json' in a: print('{}')\n")
    sandbox.env["FAKE_JUDGE_KEY"] = "sk-fake"
    blocked = sandbox.commit_all(repo, "add flag")
    out = output_of(blocked)
    assert blocked.returncode != 0, out
    assert "New CLI flags are documented in README.md" in out
    assert "README.md is untouched" in out  # the judge's reason is the instruction
    assert "96%" in out

    path, headers, body = judge.requests[0]
    assert path == "/v1/chat/completions"
    assert headers.get("Authorization") == "Bearer sk-fake"
    prompt = body["messages"][-1]["content"]
    assert "New CLI flags are documented" in prompt
    assert "Users learn flags from the README" in prompt
    assert "+    if '--json'" in prompt  # the diff, not the whole file
    assert "README.md" not in prompt.split("Staged changes in scope:")[1]  # untouched file not sent

    # Fix: document the flag → the judge (now scripted to agree) lets it through.
    judge.holds, judge.reason = True, "README now lists --json"
    sandbox.write(repo, "README.md", "# tool\n\n- --verbose\n- --json\n")
    fixed = sandbox.commit_all(repo, "document flag")
    assert fixed.returncode == 0, output_of(fixed)


def test_at_reference_hands_the_file_to_the_judge(sandbox, judge_factory):
    judge = judge_factory(holds=False, p=0.97, reason="'synergy' is on the banned list")
    repo = sandbox.repo()
    sandbox.write(repo, "banned-words.md", "# Banned\n\n- synergy\n- leverage\n")
    sandbox.write(repo, "posts/hello.md", "Hi.\n")
    assert sandbox.commit_all(repo, "seed").returncode == 0
    sandbox.write(repo, "henxels.yaml", f"""settings:
  judge: {{base_url: {judge.url}, model: fake}}
henxels:
  - henxel: "None of the words in @banned-words.md are used"
    in: ./posts/*
    make_sure_that: true
""")
    sandbox.henxels("init", cwd=repo)
    assert sandbox.commit_all(repo, "contract").returncode == 0
    judge.requests.clear()

    sandbox.write(repo, "posts/hello.md", "Hi. We leverage synergy.\n")
    blocked = sandbox.commit_all(repo, "buzzwords")
    out = output_of(blocked)
    assert blocked.returncode != 0, out
    assert "banned list" in out
    prompt = judge.requests[0][2]["messages"][-1]["content"]
    assert "@banned-words.md in the statement refers to the file below" in prompt
    assert "- synergy" in prompt and "+Hi. We leverage synergy." in prompt


def test_unsure_failure_only_warns(sandbox, judge_factory):
    judge = judge_factory(holds=False, p=0.55, reason="hard to say")
    repo = sandbox.repo()
    _seed(sandbox, repo, judge.url)
    sandbox.write(repo, "cli.py", "def main(a):\n    if '--json' in a: print('{}')\n")
    commit = sandbox.commit_all(repo, "add flag")
    out = output_of(commit)
    assert commit.returncode == 0, out
    assert "55%" in out and "New CLI flags" in out


def test_untouched_scope_never_asks_the_judge(sandbox, judge_factory):
    judge = judge_factory(holds=False, p=0.99, reason="would block if asked")
    repo = sandbox.repo()
    _seed(sandbox, repo, judge.url)
    judge.requests.clear()
    sandbox.write(repo, "notes.txt", "unrelated\n")
    commit = sandbox.commit_all(repo, "unrelated")
    assert commit.returncode == 0, output_of(commit)
    assert judge.requests == []


def test_unreachable_judge_fails_open(sandbox):
    repo = sandbox.repo()
    _seed(sandbox, repo, "http://127.0.0.1:9/v1")  # nothing listens on the discard port
    sandbox.write(repo, "cli.py", "def main(a):\n    if '--json' in a: print('{}')\n")
    commit = sandbox.commit_all(repo, "add flag")
    out = output_of(commit)
    assert commit.returncode == 0, out
    assert "could not be judged" in out


LIVE_URL = os.environ.get("HENXELS_JUDGE_URL")


@pytest.mark.skipif(not LIVE_URL, reason="set HENXELS_JUDGE_URL (and HENXELS_JUDGE_MODEL) to run against a real judge")
def test_live_judge_catches_an_undocumented_flag(sandbox):
    """A real model, a real diff: the flag is added, the README isn't — it must notice."""
    repo = sandbox.repo()
    sandbox.write(repo, "README.md", "# tool\n\nFlags:\n\n- `--verbose`: talk more\n")
    sandbox.write(repo, "cli.py", "def main(args):\n    if '--verbose' in args:\n        print('v')\n")
    seeded = sandbox.commit_all(repo, "seed")  # before the contract: the seed isn't judged
    assert seeded.returncode == 0, output_of(seeded)
    # The contract only says there IS a judge; WHERE it lives rides in on HENXELS_JUDGE_*,
    # exactly as it would on a developer's machine. Nothing LAN-specific is written to disk.
    sandbox.env.update({k: v for k, v in os.environ.items() if k.startswith("HENXELS_JUDGE_")})
    sandbox.write(repo, "henxels.yaml", """settings:
  judge: {api_key_env: HENXELS_JUDGE_KEY, timeout: 600}
henxels:
  - henxel: "New CLI flags are documented in README.md"
    in: [./cli.py, ./README.md]
    why: Users learn flags from the README, not the source.
    make_sure_that: true
""")
    sandbox.henxels("init", cwd=repo)
    contracted = sandbox.commit_all(repo, "contract")  # scope untouched → not judged
    assert contracted.returncode == 0, output_of(contracted)

    sandbox.write(repo, "cli.py", "def main(args):\n    if '--verbose' in args:\n        print('v')\n    if '--json' in args:\n        print('{}')\n")
    blocked = sandbox.commit_all(repo, "add --json flag, forget the README")
    out = output_of(blocked)
    assert blocked.returncode != 0, out
    assert "New CLI flags are documented in README.md" in out

    sandbox.write(repo, "README.md", "# tool\n\nFlags:\n\n- `--verbose`: talk more\n- `--json`: print JSON\n")
    fixed = sandbox.commit_all(repo, "document --json")
    assert fixed.returncode == 0, output_of(fixed)
