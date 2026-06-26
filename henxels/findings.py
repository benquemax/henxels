"""A *finding* is one henxel's verdict about one path.

Validators don't print; they return findings. The reporter decides how to render
them (fancy for humans, plain for machines). Every finding carries enough to teach:
what henxel, why it exists, and where to put the thing instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Severity levels.
BLOCK = "block"  # stops the action; override by editing the contract (or bless)
WARN = "warn"  # advisory; surfaced loudly but never blocks


@dataclass
class Finding:
    """One henxel verdict."""

    level: str  # BLOCK | WARN
    henxel: str  # the henxel's sentence (v2) or a short rule id (legacy)
    path: str  # the path this is about ("" when the finding spans many)
    message: str  # what's wrong, in one line
    reason: str | None = None  # why the henxel exists (from the contract)
    steer: str | None = None  # where to put it / how to comply
    fix: str | None = None  # the conscious override, if any
    details: list[str] = field(default_factory=list)  # per-file violations (v2)

    @property
    def is_block(self) -> bool:
        return self.level == BLOCK
