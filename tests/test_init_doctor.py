"""`henxels init` scaffolding and `henxels doctor` diagnostics (v2)."""

from henxels.cli import main
from henxels.contract import load_contract
from henxels.doctor import diagnose
from henxels.scaffold import detect_project, init, starter_contract


def test_detect_python(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    assert detect_project(tmp_path) == "python"


def test_starter_contracts_load(tmp_path):
    for kind in ("python", "node", "generic"):
        p = tmp_path / f"{kind}.yaml"
        p.write_text(starter_contract(kind), encoding="utf-8")
        c = load_contract(p)
        assert c.henxels  # has rules
        assert "$schema=" in starter_contract(kind)


def test_init_creates_everything(git_repo):
    (git_repo / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    report = init(git_repo)
    assert report["contract"][0] == "created"
    assert (git_repo / "henxels.yaml").is_file()
    assert (git_repo / "AGENTS.md").is_file()
    assert report["hooks"]["pre-commit"] == "installed"
    assert "henxels:begin" in (git_repo / "AGENTS.md").read_text()


def test_doctor_green_after_init(git_repo):
    (git_repo / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    init(git_repo)
    checks = diagnose(git_repo)
    assert all(c.ok for c in checks), [(c.label, c.detail) for c in checks if not c.ok]


def test_cli_init_then_doctor(git_repo, monkeypatch, capsys):
    (git_repo / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    monkeypatch.chdir(git_repo)
    assert main(["init"]) == 0
    capsys.readouterr()
    assert main(["doctor"]) == 0
    assert "henxels is ready" in capsys.readouterr().out
