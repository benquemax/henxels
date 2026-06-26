"""How was henxels invoked? So teaching messages suggest a command that actually runs.

If `henxels` isn't on the user's PATH (it lives in a project venv), telling them to run
`henxels bless push` is useless — they need `uv run henxels bless push`. The git hooks
know which form resolved them and pass it via ``HENXELS_CMD``; otherwise we sniff.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def henxels_cmd() -> str:
    """Return the command prefix to put in front of a suggested henxels subcommand."""
    from_hook = os.environ.get("HENXELS_CMD")
    if from_hook:
        return from_hook
    if shutil.which("henxels"):
        return "henxels"
    if shutil.which("uv") and Path("pyproject.toml").is_file():
        return "uv run henxels"
    if shutil.which("python3"):
        return "python3 -m henxels"
    return "python -m henxels"
