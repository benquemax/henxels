"""Rendering: fancy for humans, plain for machines.

Each finding is one henxel's verdict. We render the henxel's sentence as the header,
the concrete per-file instructions beneath it, and an optional hint (how to comply or
consciously override). Color/banners only on an interactive terminal.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable

from henxels.findings import Finding

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_GREEN = "\033[32m"

BANNER = r"""   ╭───────────────╮
   │  ╷  ╷   ╷  ╷  │   henxels
   │  ╵‖ ╵   ╵ ‖╵  │   suspenders for your repo
   │   ‖       ‖   │   keep your ADHD agent in henxels
   ╰───────────────╯"""


def is_fancy(stream=None, env: dict | None = None) -> bool:
    env = os.environ if env is None else env
    if env.get("NO_COLOR") or env.get("CI") or env.get("HENXELS_PLAIN"):
        return False
    stream = stream if stream is not None else sys.stdout
    return bool(getattr(stream, "isatty", lambda: False)())


def _c(text: str, code: str, fancy: bool) -> str:
    return f"{code}{text}{_RESET}" if fancy else text


def summarize(findings: Iterable[Finding]) -> tuple[int, int]:
    blocks = sum(1 for f in findings if f.is_block)
    warns = sum(1 for f in findings if not f.is_block)
    return blocks, warns


def render(findings: list[Finding], fancy: bool = False) -> str:
    if not findings:
        return ""
    lines: list[str] = []
    for f in findings:
        mark = "✗" if f.is_block else "!"
        color = _RED if f.is_block else _YELLOW
        header = f.henxel or f.message or "(henxel)"
        lines.append(_c(f"{mark} {header}", color, fancy))
        if f.details:
            for detail in f.details:
                lines.append(f"    {detail}")
        elif f.message and f.message != header:
            lines.append(f"    {f.message}")
        hint = f.steer or f.fix
        if hint:
            lines.append(_c(f"    → {hint}", _CYAN, fancy))
    return "\n".join(lines)


def render_summary(findings: list[Finding], fancy: bool = False) -> str:
    blocks, warns = summarize(findings)
    if blocks == 0 and warns == 0:
        return _c("✓ all henxels hold", _GREEN, fancy)
    bits = []
    if blocks:
        bits.append(_c(f"✗ {blocks} henxel{'s' if blocks != 1 else ''} snapped", _RED, fancy))
    if warns:
        bits.append(_c(f"! {warns} warning{'s' if warns != 1 else ''}", _YELLOW, fancy))
    return "  ".join(bits)
