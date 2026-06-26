"""Rendering: fancy for humans, plain for machines.

Color and banners appear only on an interactive terminal. The moment output is
piped, or ``NO_COLOR`` / ``CI`` / ``HENXELS_PLAIN`` is set, we drop to clean text so
logs and tools stay parseable. Symbols (✗ ! →) are kept either way — they're just
characters, not control codes.
"""

from __future__ import annotations

import os
import sys
from typing import Iterable

from henxels.findings import Finding

# ANSI codes (only emitted in fancy mode).
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
    """True when we may use color/banners (interactive TTY, no opt-outs set)."""
    env = os.environ if env is None else env
    if env.get("NO_COLOR") or env.get("CI") or env.get("HENXELS_PLAIN"):
        return False
    stream = stream if stream is not None else sys.stdout
    return bool(getattr(stream, "isatty", lambda: False)())


def _c(text: str, code: str, fancy: bool) -> str:
    return f"{code}{text}{_RESET}" if fancy else text


def summarize(findings: Iterable[Finding]) -> tuple[int, int]:
    """Return (blocks, warnings)."""
    blocks = sum(1 for f in findings if f.is_block)
    warns = sum(1 for f in findings if not f.is_block)
    return blocks, warns


def render(findings: list[Finding], fancy: bool = False) -> str:
    """Render findings grouped by path."""
    if not findings:
        return ""

    by_path: dict[str, list[Finding]] = {}
    for f in findings:
        by_path.setdefault(f.path, []).append(f)

    lines: list[str] = []
    for path in sorted(by_path):
        lines.append(_c(path, _BOLD, fancy))
        for f in by_path[path]:
            mark = "✗" if f.is_block else "!"
            color = _RED if f.is_block else _YELLOW
            lines.append(_c(f"  {mark} {f.henxel}: {f.message}", color, fancy))
            if f.reason:
                lines.append(f"      why: {f.reason}")
            if f.steer:
                lines.append(_c(f"      → {f.steer}", _CYAN, fancy))
            if f.fix:
                lines.append(_c(f"      bless: {f.fix}", _DIM, fancy))
    return "\n".join(lines)


def render_summary(findings: list[Finding], fancy: bool = False) -> str:
    """One-line verdict."""
    blocks, warns = summarize(findings)
    if blocks == 0 and warns == 0:
        return _c("✓ all henxels hold", _GREEN, fancy)
    bits = []
    if blocks:
        bits.append(_c(f"✗ {blocks} henxel{'s' if blocks != 1 else ''} snapped", _RED, fancy))
    if warns:
        bits.append(_c(f"! {warns} warning{'s' if warns != 1 else ''}", _YELLOW, fancy))
    return "  ".join(bits)
