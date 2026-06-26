"""Run command-gate statements (run_before_commit / run_before_push).

The command's own output streams to the terminal; a non-zero exit becomes a blocking
finding. This keeps the test/lint gate in the contract — the single source of truth.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from henxels.findings import BLOCK, Finding


def run_commands(commands: list[str], stage: str, root: Path | str) -> list[Finding]:
    findings: list[Finding] = []
    for command in commands:
        result = subprocess.run(command, shell=True, cwd=str(root))
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
