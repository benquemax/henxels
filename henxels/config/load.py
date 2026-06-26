"""Parse and lightly validate ``henxels.yaml`` — the contract.

The contract is meant to read like a document; the loader's job is to turn it into
a small, predictable object without imposing structure the user didn't write.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Filenames searched, in order, when no explicit path is given.
DEFAULT_FILENAMES = ("henxels.yaml", ".henxels.yaml", "henxels.yml", ".henxels.yml")

# The version of the contract schema this build understands.
SUPPORTED_VERSION = 1


class ConfigError(Exception):
    """Raised when the contract is missing or malformed."""


@dataclass
class Config:
    """A parsed contract."""

    version: int = SUPPORTED_VERSION
    guards: dict[str, Any] = field(default_factory=dict)
    similarity: dict[str, Any] = field(default_factory=dict)
    canonical: list[dict[str, Any]] = field(default_factory=list)
    require: list[Any] = field(default_factory=list)  # repo-root required files/folders
    checks: dict[str, Any] = field(default_factory=dict)  # commands run by the hooks
    tree: dict[str, Any] = field(default_factory=dict)
    plugins: dict[str, Any] = field(default_factory=dict)
    path: Path | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def find_config(start: Path | str = ".") -> Path | None:
    """Find the contract file at ``start`` (a repo root). Returns None if absent."""
    start = Path(start)
    for name in DEFAULT_FILENAMES:
        candidate = start / name
        if candidate.is_file():
            return candidate
    return None


def load_config(path: Path | str) -> Config:
    """Load and lightly validate the contract at ``path``."""
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"Contract file not found: {path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - message passthrough
        raise ConfigError(f"Could not parse {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"Contract at {path} must be a mapping, got {type(raw).__name__}")

    version = raw.get("henxels", SUPPORTED_VERSION)
    if not isinstance(version, int):
        raise ConfigError(f"`henxels:` version must be an integer, got {version!r}")
    if version > SUPPORTED_VERSION:
        raise ConfigError(
            f"Contract requires henxels schema v{version}, "
            f"but this build understands v{SUPPORTED_VERSION}. Upgrade henxels."
        )

    return Config(
        version=version,
        guards=_as_dict(raw.get("guards")),
        similarity=_as_dict(raw.get("similarity")),
        canonical=_as_list(raw.get("canonical")),
        require=_as_list(raw.get("require")),
        checks=_as_dict(raw.get("checks")),
        tree=_as_dict(raw.get("tree")),
        plugins=_as_dict(raw.get("plugins")),
        path=path,
        raw=raw,
    )


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]
