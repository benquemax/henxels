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
    # Resolve henxels, preferring THIS project's environment over a global install — so
    # the hook runs the version the project pins (and its extras, e.g. pymarkdownlnt for
    # markdown_lint), not whatever happens to be on PATH. Order: activated venv, ./.venv,
    # ./venv, a global `henxels`, `uv run`, then a plain python module.
    return (
        "#!/bin/sh\n"
        f"{HENXELS_MARKER}\n"
        "# Runs the henxels contract before this git action. Override consciously\n"
        "# with `henxels bless <action>` or by editing henxels.yaml.\n"
        'if [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/henxels" ]; then\n'
        '  H="$VIRTUAL_ENV/bin/henxels"\n'
        "elif [ -x .venv/bin/henxels ]; then\n"
        '  H=".venv/bin/henxels"\n'
        "elif [ -x venv/bin/henxels ]; then\n"
        '  H="venv/bin/henxels"\n'
        "elif command -v henxels >/dev/null 2>&1; then\n"
        '  H="henxels"\n'
        "elif command -v uv >/dev/null 2>&1 && [ -f pyproject.toml ]; then\n"
        '  H="uv run henxels"\n'
        "elif command -v python3 >/dev/null 2>&1; then\n"
        '  H="python3 -m henxels"\n'
        "else\n"
        '  H="python -m henxels"\n'
        "fi\n"
        f'HENXELS_CMD="$H" exec $H {subcommand} "$@"\n'
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
