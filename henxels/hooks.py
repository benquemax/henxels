"""Install henxels' git hooks idempotently.

We only ever touch a hook we own (marked with ``HENXELS_MARKER``). A pre-existing
foreign hook is left alone and reported, so we never clobber someone's setup.
"""

from __future__ import annotations

import stat
from pathlib import Path

HENXELS_MARKER = "# henxels-managed hook"

# hook name -> henxels subcommand it runs
HOOKS = {"pre-commit": "_precommit", "pre-push": "_prepush"}


def _script(subcommand: str) -> str:
    # Resolve henxels robustly: a global install first, then the project's uv env
    # (so it works without activating the venv), then a plain python module.
    return (
        "#!/bin/sh\n"
        f"{HENXELS_MARKER}\n"
        "# Runs the henxels contract before this git action. Override consciously\n"
        "# with `henxels bless <action>` or by editing henxels.yaml.\n"
        "if command -v henxels >/dev/null 2>&1; then\n"
        f'  HENXELS_CMD="henxels" exec henxels {subcommand} "$@"\n'
        "elif command -v uv >/dev/null 2>&1 && [ -f pyproject.toml ]; then\n"
        f'  HENXELS_CMD="uv run henxels" exec uv run henxels {subcommand} "$@"\n'
        "elif command -v python3 >/dev/null 2>&1; then\n"
        f'  HENXELS_CMD="python3 -m henxels" exec python3 -m henxels {subcommand} "$@"\n'
        "else\n"
        f'  HENXELS_CMD="python -m henxels" exec python -m henxels {subcommand} "$@"\n'
        "fi\n"
    )


def hooks_dir(root: Path | str) -> Path:
    return Path(root) / ".git" / "hooks"


def install_hooks(root: Path | str, force: bool = False) -> dict[str, str]:
    """Install the hooks. Returns {hook: 'installed'|'updated'|'skipped:foreign'|'no-git'}."""
    hdir = hooks_dir(root)
    if not hdir.parent.exists():  # no .git
        return {hook: "no-git" for hook in HOOKS}

    hdir.mkdir(parents=True, exist_ok=True)
    result: dict[str, str] = {}
    for hook, subcommand in HOOKS.items():
        path = hdir / hook
        if path.exists():
            existing = path.read_text(encoding="utf-8", errors="replace")
            if HENXELS_MARKER in existing:
                path.write_text(_script(subcommand), encoding="utf-8")
                _make_executable(path)
                result[hook] = "updated"
                continue
            if not force:
                result[hook] = "skipped:foreign"
                continue
        path.write_text(_script(subcommand), encoding="utf-8")
        _make_executable(path)
        result[hook] = "installed"
    return result


def hooks_status(root: Path | str) -> dict[str, bool]:
    """Whether each hook is present and henxels-managed."""
    hdir = hooks_dir(root)
    status: dict[str, bool] = {}
    for hook in HOOKS:
        path = hdir / hook
        status[hook] = path.is_file() and HENXELS_MARKER in path.read_text(
            encoding="utf-8", errors="replace"
        )
    return status


def _make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
