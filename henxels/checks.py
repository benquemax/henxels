"""Contract-declared commands the hooks run (e.g. the test suite at commit time).

    checks:
      pre_commit:
        - "uv run pytest -q"
      pre_push:
        - "uv run henxels check --all"

Output streams straight to the terminal (so you see pytest as it runs); a non-zero
exit becomes a blocking finding. This keeps the test gate in the contract — the
single source of truth — instead of a hand-edited hook script.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from henxels.config.load import Config
from henxels.findings import BLOCK, Finding


def run_checks(config: Config, stage: str, root: Path | str) -> list[Finding]:
    """Run ``checks.<stage>`` commands; return a blocking finding per failure."""
    commands = config.checks.get(stage)
    if not commands:
        return []
    if isinstance(commands, str):
        commands = [commands]

    root = Path(root)
    findings: list[Finding] = []
    for command in commands:
        # Inherit stdio so the command's own output (e.g. pytest) reaches the user.
        result = subprocess.run(command, shell=True, cwd=str(root))
        if result.returncode != 0:
            findings.append(
                Finding(
                    level=BLOCK,
                    henxel="checks",
                    path=f"({stage})",
                    message=f"`{command}` failed (exit {result.returncode})",
                    reason="a contract check must pass before this action",
                    steer="fix the failure above",
                    fix=f"or change `checks.{stage}` in henxels.yaml",
                )
            )
    return findings
