"""`henxels init` scaffolding and `henxels doctor` diagnostics."""

import subprocess

from henxels.cli import main
from henxels.config.load import load_config
from henxels.doctor import diagnose
from henxels.scaffold import detect_project, init, starter_contract


def test_detect_python(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    assert detect_project(tmp_path) == "python"


def test_detect_node(tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    assert detect_project(tmp_path) == "node"


def test_detect_generic(tmp_path):
    assert detect_project(tmp_path) == "generic"


def test_starter_contracts_are_loadable(tmp_path):
    for kind in ("python", "node", "generic"):
        p = tmp_path / f"{kind}.yaml"
        p.write_text(starter_contract(kind), encoding="utf-8")
        cfg = load_config(p)  # must parse cleanly
        assert cfg.version == 1


def test_starter_has_schema_modeline():
    assert "$schema=" in starter_contract("python")


def test_init_creates_everything(git_repo):
    (git_repo / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    report = init(git_repo)
    assert report["contract"][0] == "created"
    assert report["kind"] == "python"
    assert (git_repo / "henxels.yaml").is_file()
    assert (git_repo / "AGENTS.md").is_file()
    assert report["hooks"]["pre-commit"] == "installed"
    assert "henxels:begin" in (git_repo / "AGENTS.md").read_text()


def test_init_does_not_overwrite(tmp_path):
    (tmp_path / "henxels.yaml").write_text("henxels: 1\n", encoding="utf-8")
    report = init(tmp_path, install_git_hooks=False)
    assert report["contract"][0] == "exists"


def test_doctor_all_green_after_init(git_repo):
    (git_repo / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    init(git_repo)
    checks = diagnose(git_repo)
    assert all(c.ok for c in checks), [(c.label, c.detail) for c in checks if not c.ok]


def test_doctor_flags_missing_contract(tmp_path):
    checks = diagnose(tmp_path)
    assert any(c.label == "contract found" and not c.ok for c in checks)


def test_cli_init_then_doctor(git_repo, monkeypatch, capsys):
    (git_repo / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    monkeypatch.chdir(git_repo)
    assert main(["init"]) == 0
    capsys.readouterr()
    assert main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "henxels is ready" in out
