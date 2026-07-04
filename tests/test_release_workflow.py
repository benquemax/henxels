"""release.yml: gates that must hold given the shell it runs under.

GitHub Actions runs `run:` steps as `bash -eo pipefail` by default. That makes
`producer | grep -q pattern` a live hazard: `grep -q` closes its end of the pipe the
instant it matches, and a still-flushing producer can get SIGPIPE'd — under pipefail,
that fails the step even though the pattern WAS found (hit for real on the 0.8.0
release: catalogue output raced grep and lost). The fix is to capture full output
first, so grep only ever reads a string, never a live pipe.
"""

import re
from pathlib import Path

WORKFLOW = (Path(__file__).resolve().parent.parent / ".github" / "workflows" / "release.yml").read_text(
    encoding="utf-8"
)


def test_no_pipe_to_early_exiting_grep():
    # `live_command | grep -q ...` risks SIGPIPE-ing the producer under pipefail —
    # grep exits the instant it matches, closing a pipe the producer may still be
    # writing to. `echo "$CAPTURED" | grep -q` is fine: the left side is a fully
    # materialized string, not a live process, so there's no pipe left to break.
    EARLY_EXIT = re.compile(r"-\w*q\w*|-\w*m\s*1\b")
    for lineno, line in enumerate(WORKFLOW.splitlines(), 1):
        if "|" not in line or "grep" not in line:
            continue
        producer, _, reader = line.rpartition("|")
        if EARLY_EXIT.search(reader) and not re.match(r'\s*(echo|printf)\b', producer):
            raise AssertionError(f"release.yml:{lineno} pipes a live command into an "
                                  f"early-exiting grep — capture output first: {line.strip()!r}")


def test_npm_publish_waits_for_pypi():
    # The npm launcher pins henxels==<version>; publishing npm before PyPI exists
    # means the very first install of a new version can't resolve its engine.
    npm_job = re.search(r"\n  npm:\n(.*?)(?=\n  \w|\Z)", WORKFLOW, re.DOTALL).group(1)
    assert re.search(r"needs:\s*\[[^\]]*\bpypi\b", npm_job), "npm job must depend on pypi"


def test_smoke_job_gates_on_both_publishes():
    smoke_job = re.search(r"\n  smoke:\n(.*?)(?=\n  \w|\Z)", WORKFLOW, re.DOTALL).group(1)
    assert re.search(r"needs:\s*\[[^\]]*\bpypi\b[^\]]*\bnpm\b", smoke_job)
