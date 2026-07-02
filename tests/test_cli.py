"""End-to-end CLI (v2): check / explain / catalogue / create-new-statement."""

import pytest

from henxels.cli import main

CONTRACT = """
settings:
  warn_about_similar_files:
    above: 0.85
henxels:
  - henxel: "Docs are kebab-case markdown with a title"
    in: ./docs
    allowed_filetypes: .md
    filename_casing: kebab-case
    required_frontmatter: title
  - henxel: "No setup.py"
    forbidden_files: setup.py
"""


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "henxels.yaml").write_text(CONTRACT, encoding="utf-8")
    (tmp_path / "docs").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_check_clean(project, capsys):
    (project / "docs" / "intro.md").write_text("---\ntitle: t\n---\n# h\n", encoding="utf-8")
    assert main(["check", "--all", "--plain"]) == 0
    assert "all henxels hold" in capsys.readouterr().out


def test_check_blocks_with_instructions(project, capsys):
    (project / "docs" / "Bad_Name.md").write_text("# no frontmatter\n", encoding="utf-8")
    code = main(["check", "--all", "--plain"])
    out = capsys.readouterr().out
    assert code == 1
    assert "Docs are kebab-case markdown with a title" in out
    assert "Bad_Name" in out
    assert "title" in out


def test_check_forbidden_file(project, capsys):
    (project / "setup.py").write_text("x\n", encoding="utf-8")
    assert main(["check", "--all", "--plain"]) == 1
    assert "No setup.py" in capsys.readouterr().out


def test_explain(project, capsys):
    assert main(["explain", "docs/intro.md"]) == 0
    out = capsys.readouterr().out
    assert "Docs are kebab-case markdown" in out


def test_catalogue_lists_builtins(project, capsys):
    assert main(["catalogue"]) == 0
    out = capsys.readouterr().out
    assert "casing" in out and "forbidden_files" in out
    assert "create-new-statement" in out


def test_create_new_statement(project, capsys):
    assert main(["create-new-statement", "max_lines"]) == 0
    out = capsys.readouterr().out
    assert "henxels_checks.py" in out
    text = (project / "henxels_checks.py").read_text()
    assert "@statement(\"max_lines\"" in text
    assert "contribute" in text


def test_hook_commands_swallow_git_args(tmp_path, monkeypatch):
    # git passes "<remote> <url>" to pre-push; the hidden hook commands must accept them.
    monkeypatch.chdir(tmp_path)
    assert main(["_prepush", "origin", "git@github.com:me/repo.git"]) == 0
    assert main(["_precommit", "anything"]) == 0


def test_check_no_contract(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["check", "--all"]) == 2
    assert "No contract found" in capsys.readouterr().err


def test_version_flag(capsys):
    import pytest as _pytest

    from henxels import __version__
    from henxels.cli import main

    with _pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out
