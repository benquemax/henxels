"""Guard henxels: make push and information-loss a conscious act.

A guard is one of:
    off    — allowed (no guard)
    bless  — blocked until `henxels bless <action>` mints a matching token
    ask    — not blocked here; surfaced as a reminder (e.g. stage: ask)

The delete guard covers BOTH deleted files and net-removed lines, because small
agents lose rows through diff-edit mistakes, not just `rm`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from henxels.config.load import Config
from henxels.engine import gitinfo
from henxels.findings import BLOCK, Finding

DEFAULT_LINE_THRESHOLD = 5


def guard_mode(config: Config, action: str) -> str:
    """Return 'off' | 'bless' | 'ask' for a guarded action."""
    raw = config.guards.get(action)
    if raw is None:
        return "off"
    if isinstance(raw, dict):
        return str(raw.get("mode", "off"))
    return str(raw)


def delete_line_threshold(config: Config) -> int:
    raw = config.guards.get("delete")
    if isinstance(raw, dict) and "line_threshold" in raw:
        return int(raw["line_threshold"])
    return DEFAULT_LINE_THRESHOLD


@dataclass
class Deletions:
    """What information loss is staged right now."""

    files: list[str] = field(default_factory=list)  # deleted files
    lines: list[tuple[str, int]] = field(default_factory=list)  # (path, removed) over threshold

    @property
    def empty(self) -> bool:
        return not self.files and not self.lines

    def fingerprint(self) -> str:
        canon = "files:" + ",".join(sorted(self.files))
        canon += "|lines:" + ",".join(f"{p}:{n}" for p, n in sorted(self.lines))
        return hashlib.sha1(canon.encode("utf-8")).hexdigest()


def collect_deletions(config: Config, root: Path | str) -> Deletions:
    """Gather staged file deletions and over-threshold line removals."""
    threshold = delete_line_threshold(config)
    files = gitinfo.staged_deletions(root)
    file_set = set(files)
    lines: list[tuple[str, int]] = []
    for added, removed, path in gitinfo.staged_numstat(root):
        if path in file_set:
            continue  # already counted as a whole-file deletion
        if removed - added > threshold:
            lines.append((path, removed))
    return Deletions(files=files, lines=lines)


def deletion_finding(deletions: Deletions) -> Finding:
    """A teaching finding naming exactly what's about to be lost."""
    bits: list[str] = []
    if deletions.files:
        bits.append(f"{len(deletions.files)} file(s) deleted")
    for path, removed in deletions.lines:
        bits.append(f"{removed} lines removed from {path}")
    summary = "; ".join(bits)
    return Finding(
        level=BLOCK,
        henxel="guard:delete",
        path=", ".join(deletions.files + [p for p, _ in deletions.lines]) or "(staged diff)",
        message=f"information loss is guarded — {summary}",
        reason="diff-edit mistakes silently drop rows; deletion should be deliberate",
        steer="if every removal is intended, bless it",
        fix="henxels bless delete   (then commit again)",
    )


def push_finding() -> Finding:
    return Finding(
        level=BLOCK,
        henxel="guard:push",
        path="(push)",
        message="push is guarded — a push is hard to take back",
        reason="reflexive pushes leak half-done work and rewrite shared history",
        steer="when you really mean it, bless the push",
        fix="henxels bless push   (then push again)",
    )


def stage_reminder() -> Finding:
    """A non-blocking nudge for `stage: ask`."""
    return Finding(
        level="warn",
        henxel="guard:stage",
        path="(staging)",
        message="ask the user before staging or pushing",
        reason="the maintainer prefers to stage and push himself",
        steer="finish your edits, then ask the user to `git add` / push",
    )
