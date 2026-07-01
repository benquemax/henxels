"""Git hook installation: idempotent, never clobbers foreign hooks."""

from henxels.hooks import HENXELS_MARKER, hooks_status, install_hooks


def test_install_into_git_repo(git_repo):
    result = install_hooks(git_repo)
    assert result["pre-commit"] == "installed"
    assert result["pre-push"] == "installed"

    hook = git_repo / ".git" / "hooks" / "pre-commit"
    assert hook.is_file()
    assert HENXELS_MARKER in hook.read_text()
    # executable bit set
    assert hook.stat().st_mode & 0o111

    assert hooks_status(git_repo) == {"pre-commit": True, "pre-push": True}


def test_reinstall_updates_managed(git_repo):
    install_hooks(git_repo)
    result = install_hooks(git_repo)
    assert result["pre-commit"] == "updated"


def test_does_not_clobber_foreign(git_repo):
    hook = git_repo / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\necho mine\n", encoding="utf-8")
    result = install_hooks(git_repo)
    assert result["pre-commit"] == "skipped:foreign"
    assert "echo mine" in hook.read_text()


def test_force_overwrites_foreign(git_repo):
    hook = git_repo / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\necho mine\n", encoding="utf-8")
    result = install_hooks(git_repo, force=True)
    assert result["pre-commit"] == "installed"
    assert HENXELS_MARKER in hook.read_text()


def test_no_git_reported(tmp_path):
    result = install_hooks(tmp_path)
    assert result["pre-commit"] == "no-git"


def test_hook_prefers_project_venv_over_global(git_repo):
    install_hooks(git_repo)
    script = (git_repo / ".git" / "hooks" / "pre-commit").read_text()
    # the project's own env is checked before a global `henxels` on PATH
    assert "$VIRTUAL_ENV/bin/henxels" in script
    assert script.index(".venv/bin/henxels") < script.index("command -v henxels")


def test_hook_falls_back_to_uv_tool_run(git_repo):
    # A `uv tool install henxels` lives in an isolated env off the hook's PATH, and the
    # target repo may not be a Python project (no pyproject.toml → `uv run` is skipped).
    # `uv tool run henxels` reaches the isolated install anyway, before the python fallback.
    install_hooks(git_repo)
    script = (git_repo / ".git" / "hooks" / "pre-commit").read_text()
    assert "uv tool run henxels" in script
    assert script.index("uv run henxels") < script.index("uv tool run henxels")
    assert script.index("uv tool run henxels") < script.index("python3 -m henxels")


def test_hook_python_fallback_is_guarded_and_errors_actionably(git_repo):
    # The python `-m` fallback must only be taken when henxels actually imports there —
    # otherwise the hook fails with a bare `No module named henxels`. When nothing can run
    # henxels, teach the user instead of crashing opaquely.
    install_hooks(git_repo)
    script = (git_repo / ".git" / "hooks" / "pre-commit").read_text()
    assert "import henxels" in script  # guard the python fallback
    assert "could not find" in script.lower()  # actionable final message
    assert "--no-verify" in script  # tell them how to bypass this one commit
