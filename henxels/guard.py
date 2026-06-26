"""Git-action protections (not tests — these intercept an action).

The delete protection covers BOTH deleted files and net-removed lines, because small
agents lose rows through diff-edit mistakes, not just `rm`. Thresholds come from the
contract's ``settings:`` (see henxels.settings). Findings are v2-shaped: a sentence
header, concrete details, and the bless command as the hint.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from henxels.engine import gitinfo
from henxels.findings import BLOCK, WARN, Finding
from henxels.invocation import henxels_cmd


@dataclass
class Deletions:
    files: list[str] = field(default_factory=list)
    lines: list[tuple[str, int]] = field(default_factory=list)  # (path, removed) over threshold

    @property
    def empty(self) -> bool:
        return not self.files and not self.lines

    def fingerprint(self) -> str:
        canon = "files:" + ",".join(sorted(self.files))
        canon += "|lines:" + ",".join(f"{p}:{n}" for p, n in sorted(self.lines))
        return hashlib.sha1(canon.encode("utf-8")).hexdigest()


def collect_deletions(root: Path | str, line_threshold: int) -> Deletions:
    """Gather staged file deletions and over-threshold line removals."""
    files = gitinfo.staged_deletions(root)
    file_set = set(files)
    lines: list[tuple[str, int]] = []
    for added, removed, path in gitinfo.staged_numstat(root):
        if path in file_set:
            continue
        if removed - added > line_threshold:
            lines.append((path, removed))
    return Deletions(files=files, lines=lines)


def deletion_finding(deletions: Deletions) -> Finding:
    details = [f"{f} — file deleted" for f in deletions.files]
    details += [f"{p} — {n} lines removed" for p, n in deletions.lines]
    return Finding(
        level=BLOCK,
        henxel="Information loss is guarded — deletion should be deliberate",
        path="",
        message="",
        details=details,
        steer=f"{henxels_cmd()} bless delete   (then commit again)",
    )


def push_finding() -> Finding:
    return Finding(
        level=BLOCK,
        henxel="Push is guarded — a push is hard to take back",
        path="",
        message="",
        details=["reflexive pushes leak half-done work and rewrite shared history"],
        steer=f"{henxels_cmd()} bless push   (then push again)",
    )


def stage_reminder() -> Finding:
    return Finding(
        level=WARN,
        henxel="Ask the user before staging or pushing",
        path="",
        message="",
        details=["the maintainer prefers to stage and push himself"],
        steer="finish your edits, then ask the user to `git add` / push",
    )
