"""Conscious-override tokens — the elegant escape hatch for guards.

A guard blocks a destructive reflex (push, deleting lines/files). To proceed you run
a deliberate, non-standard verb — ``henxels bless push`` — which mints a one-time
token. The git hook then *consumes* it. A reflexive retry can't reuse the token
because it's bound to a fingerprint (the exact SHA being pushed, or the exact set of
deletions) and expires quickly.

Tokens live under ``.git/henxels/`` so they're repo-local and never committed.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

DEFAULT_TTL = 600  # seconds — a bless is a *recent* conscious act, not a standing grant


def _store_dir(root: Path | str) -> Path:
    # The *private* git dir, so a bless in one worktree never leaks into another.
    from henxels.engine.gitinfo import git_private_dir

    private = git_private_dir(root)
    return (private if private is not None else Path(root) / ".git") / "henxels"


def _token_path(root: Path | str, action: str) -> Path:
    return _store_dir(root) / f"bless-{action}.json"


def bless(root: Path | str, action: str, fingerprint: str, ttl: int = DEFAULT_TTL, now: float | None = None) -> Path:
    """Mint a one-time token for ``action`` bound to ``fingerprint``."""
    now = time.time() if now is None else now
    store = _store_dir(root)
    store.mkdir(parents=True, exist_ok=True)
    path = _token_path(root, action)
    path.write_text(
        json.dumps({"fingerprint": fingerprint, "expires_at": now + ttl}),
        encoding="utf-8",
    )
    return path


def is_blessed(root: Path | str, action: str, fingerprint: str, now: float | None = None) -> bool:
    """True if a matching, unexpired token exists (without consuming it)."""
    now = time.time() if now is None else now
    path = _token_path(root, action)
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return False
    if data.get("fingerprint") != fingerprint:
        return False
    if float(data.get("expires_at", 0)) < now:
        return False
    return True


def consume(root: Path | str, action: str, fingerprint: str, now: float | None = None) -> bool:
    """Verify a matching token and delete it. Returns True if it was valid."""
    ok = is_blessed(root, action, fingerprint, now=now)
    # Always clear the token file: a used token is spent, a stale/mismatched one is junk.
    _token_path(root, action).unlink(missing_ok=True)
    return ok


def clear(root: Path | str, action: str) -> None:
    _token_path(root, action).unlink(missing_ok=True)
