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
