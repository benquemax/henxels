"""`henxels init --template agentic-project` — scaffold the agentic project starter.

Seeds the working folders an agent-driven project leans on — `_todo.md` (parking lot),
`_temp/` (gitignored scratch), `_vision/` (the northstar book), `_plans/` (decided
work) — plus the henxels that keep them honest. Green at birth, additive only.
"""

from henxels.cli import main
from henxels.contract import apply_imports, load_contract
from henxels.runner import run_contract
from henxels.scaffold import init
from henxels.statements.registry import all_statements

SEEDS = ("_todo.md", "_vision/index.md", "_vision/northstar.md", "_plans/index.md")


def _findings(root):
    contract = load_contract(root / "henxels.yaml")
    assert apply_imports(contract, root=root) == []
    return run_contract(contract, root)


# --- empty repo: scaffold, green at birth ----------------------------------

def test_scaffold_empty_repo_is_green_at_birth(tmp_path):
    report = init(tmp_path, install_git_hooks=False, template="agentic-project")
    assert report["template"] == "agentic-project"
    for seed in SEEDS:
        assert (tmp_path / seed).is_file(), f"missing seed {seed}"
    assert _findings(tmp_path) == []


def test_temp_is_gitignored(tmp_path):
    init(tmp_path, install_git_hooks=False, template="agentic-project")
    assert "_temp/" in (tmp_path / ".gitignore").read_text(encoding="utf-8").splitlines()


def test_existing_gitignore_is_appended_not_clobbered(tmp_path):
    (tmp_path / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    init(tmp_path, install_git_hooks=False, template="agentic-project")
    lines = (tmp_path / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "node_modules/" in lines and "_temp/" in lines


def test_contract_uses_known_statements_only(tmp_path):
    init(tmp_path, install_git_hooks=False, template="agentic-project")
    contract = load_contract(tmp_path / "henxels.yaml")
    known = set(all_statements())
    for hx in contract.henxels:
        assert set(hx.statements) <= known, f"unknown statements in {hx.text!r}"


def test_compose_with_detected_project_type(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    init(tmp_path, install_git_hooks=False, template="agentic-project")
    text = (tmp_path / "henxels.yaml").read_text(encoding="utf-8")
    assert "snake_case" in text  # the python starter rode along
    assert "_vision" in text  # and the agentic henxels too
    assert text.count("henxels:") == 1 and text.count("settings:") == 1
    assert _findings(tmp_path) == []  # still green at birth


def test_secrets_rule_covers_subfolders(tmp_path):
    # `in: .` would scan only root-level files — the rule must hold repo-wide.
    init(tmp_path, install_git_hooks=False, template="agentic-project")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "creds.py").write_text('password = "supersecret123"\n', encoding="utf-8")
    assert "creds.py" in str(_findings(tmp_path))


# --- never clobber ----------------------------------------------------------

def test_existing_seed_files_are_kept(tmp_path):
    (tmp_path / "_todo.md").write_text("mine\n", encoding="utf-8")
    init(tmp_path, install_git_hooks=False, template="agentic-project")
    assert (tmp_path / "_todo.md").read_text(encoding="utf-8") == "mine\n"


def test_existing_contract_is_kept_and_fragment_offered(tmp_path):
    (tmp_path / "henxels.yaml").write_text(
        'henxels:\n  - henxel: "Mine"\n    required_files: README.md\n', encoding="utf-8"
    )
    report = init(tmp_path, install_git_hooks=False, template="agentic-project")
    assert report["contract"][0] == "exists"
    assert "Mine" in (tmp_path / "henxels.yaml").read_text(encoding="utf-8")
    assert "_vision" in report["fragment"]  # paste-able block for the user/agent
    assert not (tmp_path / "_vision").exists()  # no contract written → no seeds either


# --- CLI ---------------------------------------------------------------------

def test_cli_scaffold_reports_template_and_seeds(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--template", "agentic-project", "--no-hooks"]) == 0
    out = capsys.readouterr().out
    assert "agentic-project" in out
    assert "_vision" in out
