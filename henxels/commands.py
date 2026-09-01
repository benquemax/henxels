"""Run command-gate statements (run_before_commit / run_before_push).

The command's own output streams to the terminal; a non-zero exit becomes a blocking
finding. This keeps the test/lint gate in the contract — the single source of truth.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from henxels.findings import BLOCK, Finding

# Git exports these to hook processes; a gate command that shells out to git in
# any other directory would silently operate on the parent repo instead. Gates
# run from the repo root, so a clean git context is always the right one.
_GIT_HOOK_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_PREFIX", "GIT_COMMON_DIR")


def run_commands(commands: list[str], stage: str, root: Path | str) -> list[Finding]:
    env = {k: v for k, v in os.environ.items() if k not in _GIT_HOOK_VARS}
    findings: list[Finding] = []
    for command in commands:
        result = subprocess.run(command, shell=True, cwd=str(root), env=env)
        if result.returncode != 0:
            findings.append(
                Finding(
                    level=BLOCK,
                    henxel=f"`{command}` must pass before {stage.replace('_', ' ')}",
                    path="",
                    message="",
                    details=[f"command failed (exit {result.returncode}) — fix the failure above"],
                    steer=f"or change the run_before_{stage.split('_')[-1]} henxel in henxels.yaml",
                )
            )
    return findings
