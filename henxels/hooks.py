"""Install henxels' git hooks idempotently.

We only ever touch a hook we own (marked with ``HENXELS_MARKER``). A pre-existing
foreign hook is left alone and reported, so we never clobber someone's setup.

With ``adopt=True`` a foreign hook is instead moved to ``<hook>.local`` and
chained after the contract, so henxels and the other tool (git-lfs, husky, a
hand-rolled script) both run. Chaining beats merging: because we rewrite any
file carrying our marker, anything merged *into* our hook is silently lost on the
next install — for git-lfs that means pushes quietly stop uploading objects.
A separate file cannot be clobbered.
"""

from __future__ import annotations

import stat
from pathlib import Path

HENXELS_MARKER = "# henxels-managed hook"

# hook name -> henxels subcommand it runs
HOOKS = {"pre-commit": "_precommit", "pre-push": "_prepush"}


def _script(subcommand: str, hook: str) -> str:
    # Resolve henxels, preferring THIS project's environment over a global install — so
    # the hook runs the version the project pins (and its extras, e.g. pymarkdownlnt for
    # markdown_lint), not whatever happens to be on PATH. Order: activated venv, ./.venv,
    # ./venv, a global `henxels`, `uv run` (project), `uv tool run` (isolated tool install
    # that may be off the hook's PATH, even in a non-Python repo), then a python module —
    # but only if henxels actually imports there. If nothing can run it, teach instead of
    # dying with a bare `No module named henxels`.
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
        "elif command -v uv >/dev/null 2>&1; then\n"
        '  H="uv tool run henxels"\n'
        "elif command -v python3 >/dev/null 2>&1 && python3 -c 'import henxels' 2>/dev/null; then\n"
        '  H="python3 -m henxels"\n'
        "elif command -v python >/dev/null 2>&1 && python -c 'import henxels' 2>/dev/null; then\n"
        '  H="python -m henxels"\n'
        "else\n"
        '  echo "henxels: could not find the henxels command in this environment." >&2\n'
        '  echo "  Install it (e.g. \'uv tool install henxels\' or \'pip install henxels\')," >&2\n'
        '  echo "  or run \'henxels init\' from an env where henxels is on PATH." >&2\n'
        '  echo "  To bypass the contract for this one commit: git commit --no-verify." >&2\n'
        "  exit 1\n"
        "fi\n"
        # A chained hook must see the same stdin we were handed (pre-push gets
        # its refs there), so buffer it once and replay it to both.
        f'CHAIN="$(dirname "$0")/{hook}.local"\n'
        'if [ -x "$CHAIN" ]; then\n'
        '  IN="$(mktemp)"; cat > "$IN"\n'
        f'  HENXELS_CMD="$H" $H {subcommand} "$@" < "$IN" || {{ rc=$?; rm -f "$IN"; exit $rc; }}\n'
        '  "$CHAIN" "$@" < "$IN"; rc=$?; rm -f "$IN"; exit $rc\n'
        "fi\n"
        f'HENXELS_CMD="$H" exec $H {subcommand} "$@"\n'
    )


def hooks_dir(root: Path | str) -> Path:
    return Path(root) / ".git" / "hooks"


def install_hooks(root: Path | str, force: bool = False, adopt: bool = False) -> dict[str, str]:
    """Install the hooks.

    Returns {hook: 'installed'|'updated'|'adopted'|'skipped:foreign'|'no-git'}.
    ``adopt`` moves a foreign hook to ``<hook>.local`` and chains it instead of
    standing down; ``force`` overwrites it outright.
    """
    hdir = hooks_dir(root)
    if not hdir.parent.exists():  # no .git
        return {hook: "no-git" for hook in HOOKS}

    hdir.mkdir(parents=True, exist_ok=True)
    result: dict[str, str] = {}
    for hook, subcommand in HOOKS.items():
        path = hdir / hook
        status = "installed"
        if path.exists():
            existing = path.read_text(encoding="utf-8", errors="replace")
            if HENXELS_MARKER in existing:
                path.write_text(_script(subcommand, hook), encoding="utf-8")
                _make_executable(path)
                result[hook] = "updated"
                continue
            if adopt:
                chain = path.with_name(hook + ".local")
                path.replace(chain)
                _make_executable(chain)
                status = "adopted"
            elif not force:
                result[hook] = "skipped:foreign"
                continue
        path.write_text(_script(subcommand, hook), encoding="utf-8")
        _make_executable(path)
        result[hook] = status
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
