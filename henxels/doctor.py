"""`henxels doctor` — is the contract valid and the plumbing wired?"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from henxels.config.load import ConfigError, find_config, load_config
from henxels.engine.gitinfo import is_git_repo
from henxels.hooks import hooks_status
from henxels.rules.naming import NAMING_CONVENTIONS
from henxels.schema import schema_text


@dataclass
class Check:
    ok: bool
    label: str
    detail: str = ""


def diagnose(root: Path | str) -> list[Check]:
    """Run the health checks, returning one Check per concern."""
    root = Path(root)
    checks: list[Check] = []

    # Git
    git = is_git_repo(root)
    checks.append(Check(git, "git repository", "" if git else "guards/similarity need git"))

    # Contract present + parses
    cfg_path = find_config(root)
    if cfg_path is None:
        checks.append(Check(False, "contract found", "run `henxels init`"))
        return checks
    checks.append(Check(True, "contract found", str(cfg_path.name)))

    try:
        config = load_config(cfg_path)
        checks.append(Check(True, "contract parses", f"schema v{config.version}"))
    except ConfigError as exc:
        checks.append(Check(False, "contract parses", str(exc)))
        return checks

    # Schema parity (the bundled JSON Schema must know our naming conventions)
    try:
        enum = set(json.loads(schema_text())["$defs"]["naming"]["enum"])
        parity = enum == set(NAMING_CONVENTIONS)
        checks.append(Check(parity, "schema in sync", "" if parity else "naming enum drift"))
    except (ValueError, KeyError) as exc:  # pragma: no cover
        checks.append(Check(False, "schema in sync", str(exc)))

    # Hooks
    if git:
        status = hooks_status(root)
        for hook, present in status.items():
            checks.append(
                Check(present, f"hook: {hook}", "" if present else "run `henxels init`")
            )

    # AGENTS.md digest
    agents = root / "AGENTS.md"
    has_digest = agents.is_file() and "henxels:begin" in agents.read_text(
        encoding="utf-8", errors="replace"
    )
    checks.append(
        Check(has_digest, "AGENTS.md digest", "" if has_digest else "run `henxels sync`")
    )

    return checks
