"""Hermetic end-to-end harness: drive the real `henxels` process on a sandboxed machine.

The discipline that makes these tests end-to-end: **never import henxels here**. The
system under test is the process (`python -m henxels` by default; set
HENXELS_E2E_COMMAND to test another artifact, e.g. a wheel-installed console script or
the npm shim), plus real `git` with the hooks it installs.

The sandbox isolates everything a user's machine could leak in: HOME, global/system git
config (hooksPath, gpgsign, templates), the cache dir, and the CI/NO_COLOR variables the
harness environment happens to set — scenarios opt into those explicitly.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

E2E_COMMAND = shlex.split(os.environ.get("HENXELS_E2E_COMMAND", "")) or [sys.executable, "-m", "henxels"]

# Inherited only when present: enough to find executables and speak UTF-8, nothing more.
_KEEP = ("PATH", "LANG", "LC_ALL", "SYSTEMROOT", "COMSPEC", "TEMP", "TMP", "PYTHONIOENCODING")

_GITCONFIG = """[user]
\temail = e2e@example.com
\tname = E2E
[commit]
\tgpgsign = false
[init]
\tdefaultBranch = main
"""


class Sandbox:
    """A throwaway user machine under tmp_path."""

    def __init__(self, base: Path):
        self.base = base
        home = base / "home"
        home.mkdir(parents=True)
        gitconfig = base / "gitconfig"
        gitconfig.write_text(_GITCONFIG, encoding="utf-8")
        self.env = {k: v for k, v in os.environ.items() if k in _KEEP}
        self.env.update(
            HOME=str(home),
            USERPROFILE=str(home),
            GIT_CONFIG_GLOBAL=str(gitconfig),
            GIT_CONFIG_SYSTEM=os.devnull,
            GIT_CONFIG_NOSYSTEM="1",
            XDG_CACHE_HOME=str(base / "cache"),
            HENXELS_NO_UPDATE_CHECK="1",
        )
        self._repos = 0

    # --- processes -------------------------------------------------------
    def run(self, argv: list[str], cwd: Path, *, env_extra: dict | None = None,
            stdin_text: str | None = None) -> subprocess.CompletedProcess:
        env = {**self.env, **(env_extra or {})}
        return subprocess.run(
            argv, cwd=str(cwd), env=env, capture_output=True, text=True,
            input=stdin_text, timeout=120,
        )

    def henxels(self, *args: str, cwd: Path, env_extra: dict | None = None,
                stdin_text: str | None = None) -> subprocess.CompletedProcess:
        return self.run([*E2E_COMMAND, *args], cwd, env_extra=env_extra, stdin_text=stdin_text)

    def git(self, *args: str, cwd: Path) -> subprocess.CompletedProcess:
        return self.run(["git", *args], cwd)

    # --- repos -----------------------------------------------------------
    def repo(self) -> Path:
        self._repos += 1
        path = self.base / f"repo{self._repos}"
        path.mkdir()
        assert self.git("init", "-q", cwd=path).returncode == 0
        return path

    def bare_remote(self, repo: Path) -> Path:
        bare = self.base / f"{repo.name}-remote.git"
        assert self.run(["git", "init", "--bare", "-q", str(bare)], cwd=self.base).returncode == 0
        assert self.git("remote", "add", "origin", str(bare), cwd=repo).returncode == 0
        return bare

    # --- journey shorthand -------------------------------------------------
    def write(self, repo: Path, rel: str, content: str) -> None:
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def commit_all(self, repo: Path, message: str = "step") -> subprocess.CompletedProcess:
        """Stage everything and commit through the real hooks."""
        add = self.git("add", "-A", cwd=repo)
        assert add.returncode == 0, add.stderr
        return self.git("commit", "-m", message, cwd=repo)


def output_of(result: subprocess.CompletedProcess) -> str:
    """Combined streams — journeys assert on content, not on which stream carried it."""
    return (result.stdout or "") + (result.stderr or "")
