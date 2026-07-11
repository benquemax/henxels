"""`henxels init --template okf-llm-wiki` — scaffold a new OKF wiki or govern an existing one.

Empty repo → seed wiki, blocking rules, green at birth. Existing wiki → govern it at
`level: warn` (the findings are the migration plan). Ambiguous location → an
instructive error carrying the exact rerun command, never a silent guess.
"""

import re

import pytest

from henxels.cli import main
from henxels.contract import apply_imports, load_contract
from henxels.runner import run_contract
from henxels.scaffold import ScaffoldError, init, resolve_wiki_dir, wiki_candidates
from henxels.statements.registry import all_statements


def _findings(root):
    contract = load_contract(root / "henxels.yaml")
    assert apply_imports(contract, root=root) == []
    return run_contract(contract, root)


# --- empty repo: scaffold, green at birth ----------------------------------

def test_scaffold_empty_repo_is_green_at_birth(tmp_path):
    report = init(tmp_path, install_git_hooks=False, template="okf-llm-wiki")
    assert report["wiki"] == ("scaffolded", "wiki")
    for seed in ("wiki/index.md", "wiki/wiki-conventions.md", "wiki/log.md"):
        assert (tmp_path / seed).is_file(), f"missing seed {seed}"
    assert (tmp_path / "henxels_checks.py").is_file()
    assert _findings(tmp_path) == []


def test_scaffold_rules_block_by_default(tmp_path):
    init(tmp_path, install_git_hooks=False, template="okf-llm-wiki")
    text = (tmp_path / "henxels.yaml").read_text(encoding="utf-8")
    assert "rooted_links_resolve: ./wiki" in text
    assert "level: warn" not in text  # nothing to migrate → enforce from birth
    assert "frontmatter_values" in text  # taxonomy ships commented out, ready to pin
    assert "# frontmatter_values" in text or "#   frontmatter_values" in text


def test_scaffold_seeds_declare_okf_version_and_today(tmp_path):
    import datetime

    init(tmp_path, install_git_hooks=False, template="okf-llm-wiki")
    assert 'okf_version: "0.1"' in (tmp_path / "wiki/index.md").read_text(encoding="utf-8")
    today = datetime.date.today().isoformat()
    assert today in (tmp_path / "wiki/log.md").read_text(encoding="utf-8")
    assert today in (tmp_path / "wiki/wiki-conventions.md").read_text(encoding="utf-8")


def test_template_contract_uses_known_statements_only(tmp_path):
    init(tmp_path, install_git_hooks=False, template="okf-llm-wiki")
    contract = load_contract(tmp_path / "henxels.yaml")
    apply_imports(contract, root=tmp_path)  # registers the scaffolded custom check
    known = set(all_statements())
    for hx in contract.henxels:
        assert set(hx.statements) <= known, f"unknown statements in {hx.text!r}"


def test_compose_with_detected_project_type(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    init(tmp_path, install_git_hooks=False, template="okf-llm-wiki")
    text = (tmp_path / "henxels.yaml").read_text(encoding="utf-8")
    assert "snake_case" in text  # the python starter rode along
    assert "rooted_links_resolve" in text  # and the wiki henxels too
    # exactly one top-level henxels: / settings: block (match at line start so
    # requires_henxels: doesn't count as a second henxels:)
    assert len(re.findall(r"(?m)^henxels:", text)) == 1
    assert len(re.findall(r"(?m)^settings:", text)) == 1
    assert _findings(tmp_path) == []  # still green at birth


# --- existing wiki: govern at warn, write nothing into it ------------------

def _existing_wiki(tmp_path, dirname="wiki"):
    d = tmp_path / dirname
    d.mkdir(parents=True)
    (d / "notes.md").write_text("Some pre-henxels knowledge, no frontmatter.\n", encoding="utf-8")
    return d


def test_existing_wiki_is_governed_at_warn(tmp_path):
    _existing_wiki(tmp_path)
    report = init(tmp_path, install_git_hooks=False, template="okf-llm-wiki")
    assert report["wiki"] == ("governing", "wiki")
    assert not (tmp_path / "wiki/wiki-conventions.md").exists()  # no seeds into their wiki
    assert "level: warn" in (tmp_path / "henxels.yaml").read_text(encoding="utf-8")
    findings = _findings(tmp_path)
    assert findings, "a non-conformant wiki must yield the migration plan"
    assert all(f.level == "warn" for f in findings)


def test_existing_wiki_content_is_untouched(tmp_path):
    d = _existing_wiki(tmp_path)
    before = (d / "notes.md").read_text(encoding="utf-8")
    init(tmp_path, install_git_hooks=False, template="okf-llm-wiki")
    assert (d / "notes.md").read_text(encoding="utf-8") == before


def test_custom_wiki_dir(tmp_path):
    report = init(tmp_path, install_git_hooks=False, template="okf-llm-wiki", wiki_dir="pages")
    assert report["wiki"] == ("scaffolded", "pages")
    assert (tmp_path / "pages/index.md").is_file()
    text = (tmp_path / "henxels.yaml").read_text(encoding="utf-8")
    assert "rooted_links_resolve: ./pages" in text and "referenced_in: pages/index.md" in text
    assert _findings(tmp_path) == []


# --- wiki location: default, candidates, explicitness ----------------------

def test_wiki_candidates_threshold_and_excludes(tmp_path):
    for i in range(3):
        p = tmp_path / "pages" / f"p{i}.md"
        p.parent.mkdir(exist_ok=True)
        p.write_text("x\n", encoding="utf-8")
    (tmp_path / "thin").mkdir()
    (tmp_path / "thin/one.md").write_text("x\n", encoding="utf-8")
    (tmp_path / "node_modules/dep").mkdir(parents=True)
    for i in range(5):
        (tmp_path / "node_modules/dep" / f"d{i}.md").write_text("x\n", encoding="utf-8")
    names = [name for name, _ in wiki_candidates(tmp_path)]
    assert names == ["pages"]  # ≥3 md files; excludes noise dirs and the thin one


def test_default_wiki_dir_wins_when_present(tmp_path):
    _existing_wiki(tmp_path, "wiki")
    _existing_wiki(tmp_path, "pages")
    assert resolve_wiki_dir(tmp_path) == "wiki"


def test_ambiguous_location_error_is_an_instruction(tmp_path):
    for i in range(4):
        p = tmp_path / "pages" / f"p{i}.md"
        p.parent.mkdir(exist_ok=True)
        p.write_text("x\n", encoding="utf-8")
    with pytest.raises(ScaffoldError) as exc:
        init(tmp_path, install_git_hooks=False, template="okf-llm-wiki")
    message = str(exc.value)
    assert "pages" in message
    assert "henxels init --template okf-llm-wiki --wiki-dir pages" in message
    assert not (tmp_path / "henxels.yaml").exists()  # decided nothing → wrote nothing


def test_ask_callback_settles_ambiguity(tmp_path):
    for i in range(4):
        p = tmp_path / "pages" / f"p{i}.md"
        p.parent.mkdir(exist_ok=True)
        p.write_text("x\n", encoding="utf-8")
    report = init(tmp_path, install_git_hooks=False, template="okf-llm-wiki", ask=lambda cands: "pages")
    assert report["wiki"] == ("governing", "pages")


# --- never clobber ----------------------------------------------------------

def test_existing_contract_is_kept_and_fragment_offered(tmp_path):
    (tmp_path / "henxels.yaml").write_text("henxels:\n  - henxel: \"Mine\"\n    required_files: README.md\n", encoding="utf-8")
    report = init(tmp_path, install_git_hooks=False, template="okf-llm-wiki")
    assert report["contract"][0] == "exists"
    assert "Mine" in (tmp_path / "henxels.yaml").read_text(encoding="utf-8")
    assert "rooted_links_resolve" in report["fragment"]  # paste-able block for the user/agent


def test_existing_checks_file_is_kept(tmp_path):
    (tmp_path / "henxels_checks.py").write_text("# mine\n", encoding="utf-8")
    report = init(tmp_path, install_git_hooks=False, template="okf-llm-wiki")
    assert (tmp_path / "henxels_checks.py").read_text(encoding="utf-8") == "# mine\n"
    assert report["checks_file"][0] == "exists"


# --- dry run ------------------------------------------------------------------

def test_dry_run_writes_nothing(tmp_path):
    report = init(tmp_path, install_git_hooks=False, template="okf-llm-wiki", dry_run=True)
    assert report["dry_run"] is True
    assert report["wiki"] == ("scaffolded", "wiki")
    assert list(tmp_path.iterdir()) == []  # not a single file


# --- CLI ------------------------------------------------------------------------

def test_cli_scaffold_reports_green_at_birth(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--template", "okf-llm-wiki", "--no-hooks"]) == 0
    out = capsys.readouterr().out
    assert "green at birth" in out
    assert "→ agent:" in out


def test_cli_existing_wiki_reports_migration_plan(tmp_path, monkeypatch, capsys):
    _existing_wiki(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--template", "okf-llm-wiki", "--no-hooks"]) == 0
    out = capsys.readouterr().out
    assert "migration plan" in out
    assert "level: warn" in out


def test_cli_ambiguity_exits_with_instruction(tmp_path, monkeypatch, capsys):
    for i in range(4):
        p = tmp_path / "pages" / f"p{i}.md"
        p.parent.mkdir(exist_ok=True)
        p.write_text("x\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--template", "okf-llm-wiki", "--no-hooks"]) == 1
    out = capsys.readouterr()
    assert "--wiki-dir pages" in out.out + out.err


def test_cli_unknown_template_is_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        main(["init", "--template", "shiny-new-thing"])


def test_cli_dry_run(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--template", "okf-llm-wiki", "--no-hooks", "--dry-run"]) == 0
    assert "dry run" in capsys.readouterr().out
    assert not (tmp_path / "henxels.yaml").exists()
