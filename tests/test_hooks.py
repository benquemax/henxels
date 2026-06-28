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
