"""Git hook installation: idempotent, never clobbers foreign hooks."""

import subprocess

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


def test_adopts_foreign_hook_by_chaining(git_repo):
    # A foreign hook (git-lfs, husky, a hand-rolled script) must keep running.
    # We move it aside and call it after the contract, so both tools work and
    # neither owns the other's file.
    hook = git_repo / ".git" / "hooks" / "pre-push"
    hook.write_text("#!/bin/sh\ngit lfs pre-push \"$@\"\n", encoding="utf-8")
    result = install_hooks(git_repo, adopt=True)

    assert result["pre-push"] == "adopted"
    chained = git_repo / ".git" / "hooks" / "pre-push.local"
    assert "git lfs pre-push" in chained.read_text()
    assert chained.stat().st_mode & 0o111
    script = hook.read_text()
    assert HENXELS_MARKER in script
    assert "pre-push.local" in script


def test_reinstall_keeps_the_chain(git_repo):
    # The regression that motivated this: henxels rewrites any hook carrying its
    # marker, so anything merged *into* that file is silently lost on the next
    # `henxels init` — for git-lfs that means pushes stop uploading objects.
    # Chained hooks live in their own file, so re-installing cannot destroy them.
    hook = git_repo / ".git" / "hooks" / "pre-push"
    hook.write_text("#!/bin/sh\ngit lfs pre-push \"$@\"\n", encoding="utf-8")
    install_hooks(git_repo, adopt=True)
    install_hooks(git_repo)

    assert "git lfs pre-push" in (git_repo / ".git" / "hooks" / "pre-push.local").read_text()
    assert "pre-push.local" in hook.read_text()


def test_chained_hook_receives_stdin_and_args(git_repo):
    # pre-push gets its refs on stdin. Running the contract first must not eat
    # them — git-lfs reads the same stream to decide what to upload.
    hooks = git_repo / ".git" / "hooks"
    seen = git_repo / "seen.txt"
    (hooks / "pre-push").write_text(
        f'#!/bin/sh\n{{ printf "args=%s\\n" "$*"; cat; }} > "{seen}"\n', encoding="utf-8"
    )
    install_hooks(git_repo, adopt=True)

    # neutralise the contract half; this test is about the chain, not the check
    script = (hooks / "pre-push").read_text().replace("$H _prepush", "true")
    (hooks / "pre-push").write_text(script, encoding="utf-8")

    subprocess.run(
        [str(hooks / "pre-push"), "origin", "git@host:repo.git"],
        input="refs/heads/main abc refs/heads/main def\n",
        text=True,
        cwd=git_repo,
        check=True,
    )
    assert "refs/heads/main abc" in seen.read_text()
    assert "args=origin git@host:repo.git" in seen.read_text()


def test_adopt_is_opt_in(git_repo):
    # Without adopt=True the old behaviour stands: never touch a foreign hook.
    hook = git_repo / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\necho mine\n", encoding="utf-8")
    assert install_hooks(git_repo)["pre-commit"] == "skipped:foreign"
    assert "echo mine" in hook.read_text()
    assert not (git_repo / ".git" / "hooks" / "pre-commit.local").exists()


def test_init_adopts_with_flag_and_teaches_without_it(git_repo, monkeypatch, capsys):
    from henxels.cli import main

    monkeypatch.chdir(git_repo)
    (git_repo / ".git" / "hooks" / "pre-push").write_text(
        "#!/bin/sh\ngit lfs pre-push \"$@\"\n", encoding="utf-8"
    )

    main(["init"])
    out = capsys.readouterr().out
    assert "skipped:foreign" in out
    assert "--adopt-hooks" in out  # the way out is discoverable, not buried in docs

    main(["init", "--adopt-hooks"])
    assert "adopted" in capsys.readouterr().out
    assert (git_repo / ".git" / "hooks" / "pre-push.local").is_file()


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
