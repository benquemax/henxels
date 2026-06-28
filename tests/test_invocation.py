"""Teaching messages should suggest a command that actually runs in the user's shell."""

from henxels.invocation import henxels_cmd


def test_env_override_wins(monkeypatch):
    monkeypatch.setenv("HENXELS_CMD", "uv run henxels")
    assert henxels_cmd() == "uv run henxels"


def test_falls_back_to_something(monkeypatch):
    monkeypatch.delenv("HENXELS_CMD", raising=False)
    assert henxels_cmd()  # always returns a usable invocation


def test_push_finding_uses_invocation(monkeypatch):
    monkeypatch.setenv("HENXELS_CMD", "uv run henxels")
    from henxels.guard import push_finding

    assert "uv run henxels bless push" in push_finding().steer


def test_venv_path_prettified_to_uv_run(monkeypatch, tmp_path):
    # The hook hands us a venv-binary path; in a uv project show `uv run henxels` instead.
    monkeypatch.setenv("HENXELS_CMD", ".venv/bin/henxels")
    monkeypatch.setattr("henxels.invocation.shutil.which", lambda name: "/usr/bin/uv" if name == "uv" else None)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    assert henxels_cmd() == "uv run henxels"


def test_idiomatic_forms_pass_through(monkeypatch):
    for value in ("henxels", "uv run henxels", "python3 -m henxels"):
        monkeypatch.setenv("HENXELS_CMD", value)
        assert henxels_cmd() == value
