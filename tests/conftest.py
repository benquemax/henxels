"""Shared fixtures: a real temp git repo for guard/hook tests."""

import shutil
import subprocess

import pytest

GIT = shutil.which("git")


@pytest.fixture(autouse=True)
def _no_ambient_judge(monkeypatch):
    """A developer's shell carries HENXELS_JUDGE_* (that's the point of them); the unit
    tests must see only what they set themselves."""
    for name in ("HENXELS_JUDGE_URL", "HENXELS_JUDGE_MODEL", "HENXELS_JUDGE_TIMEOUT", "HENXELS_JUDGE_EXTRA_BODY"):
        monkeypatch.delenv(name, raising=False)


def _git(root, *args):
    subprocess.run([GIT, *args], cwd=root, check=True, capture_output=True, text=True)


@pytest.fixture
def git_repo(tmp_path):
    """An initialized git repo with identity set, in tmp_path."""
    if GIT is None:  # pragma: no cover
        pytest.skip("git not available")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "commit", "--allow-empty", "-q", "-m", "root")
    return tmp_path


@pytest.fixture
def git(tmp_path):
    """Helper to run git commands in a given root."""
    def run(root, *args):
        _git(root, *args)
    return run
