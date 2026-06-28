"""Optional "you're on an old henxels" nudge.

Designed to be invisible when it shouldn't speak: it never blocks, never errors out a
command, stays silent in CI and when offline, caches the PyPI lookup for a day, and can
be turned off with HENXELS_NO_UPDATE_CHECK. It runs only on the user-facing commands
(`check`, `doctor`) — never in the git-hook path, so commits/pushes stay fast.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

PYPI_URL = "https://pypi.org/pypi/henxels/json"
CACHE_TTL = 86400  # re-check PyPI at most once a day
_UNSET = object()


def installed_version() -> str | None:
    try:
        return version("henxels")
    except PackageNotFoundError:
        return None


def update_notice(installed=_UNSET, latest=_UNSET, env: dict | None = None) -> str | None:
    """A one-line "upgrade available" string, or None when there's nothing to say."""
    env = os.environ if env is None else env
    if env.get("HENXELS_NO_UPDATE_CHECK") or env.get("CI"):
        return None
    inst = installed_version() if installed is _UNSET else installed
    if not inst:
        return None
    lat = latest_version() if latest is _UNSET else latest
    if not lat:
        return None
    try:
        if _parse(inst) >= _parse(lat):
            return None
    except (TypeError, ValueError):
        return None
    return (
        f"↑ henxels {lat} is available (you have {inst}) — upgrade: uv tool upgrade henxels "
        f"(or pipx/pip -U), then run `henxels init` to refresh hooks + schema"
    )


def latest_version(timeout: float = 1.5, now: float | None = None) -> str | None:
    """The newest version on PyPI, cached for a day. None if it can't be determined."""
    now = time.time() if now is None else now
    cached = _read_cache()
    if cached and (now - cached.get("checked_at", 0)) < CACHE_TTL:
        return cached.get("version")
    fetched = _fetch_pypi(timeout)
    if fetched:
        _write_cache(fetched, now)
        return fetched
    return cached.get("version") if cached else None  # fall back to stale cache when offline


def _parse(v: str) -> tuple[int, ...]:
    parts = []
    for chunk in str(v).split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _fetch_pypi(timeout: float) -> str | None:
    try:
        with urllib.request.urlopen(PYPI_URL, timeout=timeout) as resp:  # noqa: S310 (https only)
            return json.load(resp)["info"]["version"]
    except Exception:  # noqa: BLE001 - offline / slow / malformed: stay silent
        return None


def _cache_path() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "henxels" / "latest.json"


def _read_cache() -> dict | None:
    try:
        return json.loads(_cache_path().read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - missing / unreadable cache is fine
        return None


def _write_cache(latest: str, now: float) -> None:
    try:
        path = _cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"version": latest, "checked_at": now}), encoding="utf-8")
    except OSError:
        pass  # a read-only cache dir shouldn't break the command
