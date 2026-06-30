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
    # local schema copy for offline / private-repo editor autocomplete
    schema = git_repo / ".henxels" / "henxels.schema.json"
    assert schema.is_file()
    assert "henxels contract" in schema.read_text()
    assert "$schema=./.henxels/henxels.schema.json" in (git_repo / "henxels.yaml").read_text()


def test_doctor_green_after_init(git_repo):
    (git_repo / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    init(git_repo)
    checks = diagnose(git_repo)
    assert all(c.ok for c in checks), [(c.label, c.detail) for c in checks if not c.ok]


def test_doctor_flags_missing_markdown_linter(git_repo, monkeypatch):
    (git_repo / "henxels.yaml").write_text(
        'henxels:\n  - henxel: "Docs lint"\n    in: ./docs\n    markdown_lint: true\n', encoding="utf-8"
    )
    from henxels.statements.builtins import content

    monkeypatch.setattr(content, "_pymarkdown_cmd", lambda: None)
    checks = diagnose(git_repo)
    md = next(c for c in checks if c.label == "markdown_lint ready")
    assert not md.ok and "pymarkdownlnt" in md.detail


def test_cli_init_then_doctor(git_repo, monkeypatch, capsys):
    (git_repo / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    monkeypatch.chdir(git_repo)
    assert main(["init"]) == 0
    capsys.readouterr()
    assert main(["doctor"]) == 0
    assert "henxels is ready" in capsys.readouterr().out


def test_doctor_flags_shadowed_hooks(git_repo, git):
    """A foreign core.hooksPath (e.g. husky) makes git ignore .git/hooks — so the hooks
    we install there never run. doctor must report that, not a misleading green."""
    (git_repo / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    init(git_repo)  # writes henxels' hooks into .git/hooks
    git(git_repo, "config", "core.hooksPath", ".husky/_")  # git now looks elsewhere
    pre = next(c for c in diagnose(git_repo) if c.label == "hook: pre-commit")
    assert not pre.ok
    assert "core.hooksPath" in pre.detail  # actionable: says why they won't fire


def test_init_warns_when_core_hookspath_shadows(git_repo, git, monkeypatch, capsys):
    """If core.hooksPath already points away from .git/hooks, init should warn that the
    freshly-installed hooks won't fire, rather than printing a bare success."""
    (git_repo / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    git(git_repo, "config", "core.hooksPath", ".husky/_")
    monkeypatch.chdir(git_repo)
    assert main(["init"]) == 0
    assert "core.hooksPath" in capsys.readouterr().out


def test_init_suggests_documenting_install_in_readme(git_repo, monkeypatch, capsys):
    """The committed contract depends on henxels being installed, so init's next steps
    should tell adopters to document the install in their repo's README."""
    (git_repo / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    monkeypatch.chdir(git_repo)
    assert main(["init"]) == 0
    out = capsys.readouterr().out
    readme_lines = [ln for ln in out.splitlines() if "README" in ln]
    assert readme_lines, "init should mention documenting henxels in the README"
    assert any("install" in ln.lower() for ln in readme_lines)
