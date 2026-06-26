"""End-to-end CLI behavior for `check` and `explain`."""

import pytest

from henxels.cli import main

CONTRACT = """
henxels: 1
tree:
  src:
    naming: snake_case
    forbid:
      - glob: "**/*_test.py"
        reason: "tests live in tests/"
        steer: "use tests/"
    api:
      require:
        - file: handlers.py
          reason: "expose handlers"
"""


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "henxels.yaml").write_text(CONTRACT, encoding="utf-8")
    (tmp_path / "src" / "api").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_check_clean(project, capsys):
    (project / "src" / "api" / "handlers.py").write_text("x", encoding="utf-8")
    code = main(["check", "--all", "--plain"])
    out = capsys.readouterr().out
    assert code == 0
    assert "all henxels hold" in out


def test_check_blocks_placement(project, capsys):
    (project / "src" / "api" / "handlers.py").write_text("x", encoding="utf-8")
    (project / "src" / "api" / "thing_test.py").write_text("x", encoding="utf-8")
    code = main(["check", "--all", "--plain"])
    out = capsys.readouterr().out
    assert code == 1
    assert "placement" in out
    assert "tests live in tests/" in out


def test_check_missing_required(project, capsys):
    # handlers.py absent -> require henxel snaps
    code = main(["check", "--all", "--plain"])
    out = capsys.readouterr().out
    assert code == 1
    assert "require" in out
    assert "handlers.py" in out


def test_check_specific_path_skips_existence(project, capsys):
    code = main(["check", "--plain", "src/api/notes.py"])
    out = capsys.readouterr().out
    assert code == 0  # naming ok, existence not run for explicit paths
    assert "all henxels hold" in out


def test_explain_command(project, capsys):
    code = main(["explain", "src/api/foo_test.py"])
    out = capsys.readouterr().out
    assert code == 0
    assert "FORBIDDEN" in out


def test_check_no_contract(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = main(["check", "--all"])
    err = capsys.readouterr().err
    assert code == 2
    assert "No contract found" in err
