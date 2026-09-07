"""`henxels init --template brainpick-brain` — scaffold a brainpick-compatible brain.

A brain is a wiki meant to be an agent's memory: `_brain/` with five memory-type
folders (knowledge, skills, journal, vision, plans), a declared data flow
(journal → knowledge → skills, read in reverse), inline grounding, and a first
skill that teaches the agent how to use and improve it. The format is
brainpick's spec/85; this template is its scaffold. Green at birth, additive only.
"""

import datetime

from henxels.cli import main
from henxels.contract import apply_imports, load_contract
from henxels.runner import run_contract
from henxels.scaffold import BRAIN_DIR, init
from henxels.statements.registry import all_statements

TEMPLATE = "brainpick-brain"
FOLDERS = ("knowledge", "skills", "journals", "vision", "plans", "raw")
SEEDS = (
    "_brain/index.md",
    "_brain/log.md",
    "_brain/knowledge/index.md",
    "_brain/skills/using-the-brain.md",
    "_brain/journals/index.md",
    "_brain/vision/index.md",
    "_brain/plans/index.md",
    "_brain/raw/index.md",
    "_todo.md",
    "brainpick.toml",
)


def _findings(root):
    contract = load_contract(root / "henxels.yaml")
    assert apply_imports(contract, root=root) == []
    return run_contract(contract, root)


def _read(root, rel):
    return (root / rel).read_text(encoding="utf-8")


def _today():
    return datetime.date.today().isoformat()


# --- empty repo: scaffold, green at birth ----------------------------------

def test_scaffold_empty_repo_is_green_at_birth(tmp_path):
    report = init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    assert report["template"] == TEMPLATE
    assert BRAIN_DIR == "_brain"
    for seed in SEEDS:
        assert (tmp_path / seed).is_file(), f"missing seed {seed}"
    for folder in FOLDERS:
        assert (tmp_path / "_brain" / folder).is_dir()
    assert (tmp_path / "henxels_checks.py").is_file()  # log_headings_are_dates rides along
    assert _findings(tmp_path) == []


def test_first_skill_teaches_the_data_flow(tmp_path):
    init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    skill = _read(tmp_path, "_brain/skills/using-the-brain.md")
    assert skill.startswith("---\n")
    assert "type: playbook" in skill
    assert "description: Use when" in skill  # a trigger, not a summary — it decides whether the body loads
    assert "export: agent-skill" in skill
    for word in ("skills/", "knowledge/", "journals/", "raw/"):
        assert word in skill
    assert "not the truth" in skill
    assert "closest" in skill  # subsidiarity
    assert "archive/" in skill  # the month roll is the agent's job
    assert "clean" in skill  # raw/ is kept in order, not a dump
    assert "github.com/benquemax/brainpick" in skill  # the pointer onward
    assert _today() in skill


def test_brainpick_toml_declares_a_brain(tmp_path):
    init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    toml = _read(tmp_path, "brainpick.toml")
    assert "[bundle]" in toml and 'root = "_brain"' in toml
    assert "[brain]" in toml and "format = 1" in toml
    assert "audience" in toml
    assert "\nid = " not in toml  # identity is minted by `brainpick init`, never by this template


def test_todo_and_temp_stay_beside_the_brain(tmp_path):
    init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    assert (tmp_path / "_todo.md").is_file()
    assert not (tmp_path / "_brain" / "_todo.md").exists()
    lines = _read(tmp_path, ".gitignore").splitlines()
    assert "_temp/" in lines and "brainpick.local.toml" in lines and ".brainpick/" in lines


def test_contract_uses_known_statements_only(tmp_path):
    init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    contract = load_contract(tmp_path / "henxels.yaml")
    apply_imports(contract, root=tmp_path)
    known = set(all_statements())
    for hx in contract.henxels:
        assert set(hx.statements) <= known, f"unknown statements in {hx.text!r}"


def test_contract_covers_the_sixteen_rules(tmp_path):
    init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    text = _read(tmp_path, "henxels.yaml")
    for needle in (
        "brainpick compile --check-fresh",        # 1 fresh before commit
        "only_these_subfolders",                  # 2 folders are memory types
        "depends_on",                             # 3 skill tree
        "type: [playbook]",                       # 3 skills are actionable
        "allowed_filetypes",                      # 4 what counts as brain material
        "git check-ignore -q _temp",              # 5 scratch
        "required_frontmatter: [type, title, description]",  # 6
        "bump_updated_on_change: timestamp",      # 7
        "no_frontmatter: true",                   # 8
        "referenced_in",                          # 9
        "rooted_links_resolve",                   # 10
        "filename_matches_regex",                 # 11 journal naming
        "journals/archive",                       # 11 history without the bulk
        "no_secrets: true",                       # 13
        "brainpick.local.toml",                   # 13 local config never committed
        "min_outbound_links",                     # grounding
    ):
        assert needle in text, f"contract lacks {needle!r}"
    assert "github.com/benquemax/brainpick" in text  # the backlink


def test_contract_fails_ungrounded_knowledge(tmp_path):
    init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    (tmp_path / "_brain/knowledge/lonely.md").write_text(
        "---\ntype: article\ntitle: Lonely\ndescription: No sources.\n"
        f"timestamp: {_today()}T00:00:00Z\n---\n\n# Lonely\n\nA claim from nowhere.\n",
        encoding="utf-8",
    )
    assert any("lonely.md" in str(f) for f in _findings(tmp_path))


def _month():
    return datetime.date.today().strftime("%Y-%m")


def _journal(*days, up="../"):
    body = "# Journal\n\n"
    for day in days:
        body += f"## {day}\n\n* Something happened. See [Using the brain]({up}skills/using-the-brain.md).\n\n"
    return body


def test_scaffold_seeds_the_current_month_journal(tmp_path):
    init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    month = tmp_path / "_brain/journals" / f"{_month()}.md"
    assert month.is_file()
    text = month.read_text(encoding="utf-8")
    assert f"## {_today()}" in text
    assert not text.startswith("---")  # a journal is a log: dated sections, no frontmatter
    assert not (tmp_path / "_brain/journals/archive").exists()  # born on the first roll


def test_contract_fails_misnamed_journal_file(tmp_path):
    init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    (tmp_path / "_brain/journals/notes.md").write_text(_journal(_today()), encoding="utf-8")
    assert any("notes.md" in str(f) for f in _findings(tmp_path))


def test_contract_fails_a_journal_heading_that_is_not_a_date(tmp_path):
    init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    month = tmp_path / "_brain/journals" / f"{_month()}.md"
    month.write_text("# Journal\n\n## Monday\n\n* Stuff.\n", encoding="utf-8")
    assert any(f"{_month()}.md" in str(f) for f in _findings(tmp_path))


def test_contract_fails_journal_days_out_of_order(tmp_path):
    init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    month = tmp_path / "_brain/journals" / f"{_month()}.md"
    month.write_text(_journal("2020-01-01", "2020-01-02"), encoding="utf-8")  # oldest first
    assert any(f"{_month()}.md" in str(f) for f in _findings(tmp_path))


def test_contract_fails_two_unarchived_months(tmp_path):
    # a new month started and the old file was not rolled into archive/
    init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    (tmp_path / "_brain/journals/2020-01.md").write_text(_journal("2020-01-02", "2020-01-01"),
                                                          encoding="utf-8")
    assert any("2020-01.md" in str(f) for f in _findings(tmp_path))


def test_archived_months_pass(tmp_path):
    init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    archive = tmp_path / "_brain/journals/archive"
    archive.mkdir()
    (archive / "2020-01.md").write_text(_journal("2020-01-02", "2020-01-01", up="../../"), encoding="utf-8")
    (archive / "2020-02.md").write_text(_journal("2020-02-01", up="../../"), encoding="utf-8")
    assert _findings(tmp_path) == []


def test_archive_rejects_a_misnamed_file(tmp_path):
    init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    (tmp_path / "_brain/journals/archive").mkdir()
    (tmp_path / "_brain/journals/archive/old-notes.md").write_text(_journal("2020-01-01"),
                                                                    encoding="utf-8")
    assert any("old-notes.md" in str(f) for f in _findings(tmp_path))


def test_raw_is_governed_but_not_okf(tmp_path):
    init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    raw = tmp_path / "_brain/raw"
    (raw / "meeting-2020-01-01.md").write_text("Plain notes, no frontmatter, no links.\n", encoding="utf-8")
    (raw / "export.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    assert _findings(tmp_path) == []  # raw material needs no frontmatter or links
    (raw / "Meeting Notes.md").write_text("x\n", encoding="utf-8")
    assert any("Meeting Notes.md" in str(f) for f in _findings(tmp_path))  # but stays orderly


def test_raw_is_excluded_from_brainpick_results(tmp_path):
    init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    toml = (tmp_path / "brainpick.toml").read_text(encoding="utf-8")
    assert 'exclude = ["raw/' in toml  # grep it, ground on it, never surface it


def test_contract_rejects_a_skill_that_is_not_a_playbook(tmp_path):
    init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    (tmp_path / "_brain/skills/essay.md").write_text(
        "---\ntype: article\ntitle: Essay\ndescription: Not a procedure.\n"
        f"timestamp: {_today()}T00:00:00Z\n---\n\n# Essay\n\n"
        "See [Using the brain](using-the-brain.md).\n",
        encoding="utf-8",
    )
    assert any("essay.md" in str(f) for f in _findings(tmp_path))


def test_contract_rejects_a_sixth_memory_type(tmp_path):
    init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    (tmp_path / "_brain" / "ideas").mkdir()
    (tmp_path / "_brain" / "ideas" / "x.md").write_text("# x\n", encoding="utf-8")
    assert any("ideas" in str(f) for f in _findings(tmp_path))


def test_compose_with_detected_project_type(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    text = _read(tmp_path, "henxels.yaml")
    assert "snake_case" in text  # the python starter rode along
    assert "_brain" in text
    assert text.count("henxels:") == 1 and text.count("settings:") == 1
    assert _findings(tmp_path) == []


# --- never clobber ----------------------------------------------------------

def test_existing_seed_files_are_kept(tmp_path):
    (tmp_path / "_todo.md").write_text("mine\n", encoding="utf-8")
    (tmp_path / "brainpick.toml").write_text('spec = "0.1"\n', encoding="utf-8")
    init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    assert _read(tmp_path, "_todo.md") == "mine\n"
    assert _read(tmp_path, "brainpick.toml") == 'spec = "0.1"\n'


def test_existing_contract_is_kept_and_fragment_offered(tmp_path):
    (tmp_path / "henxels.yaml").write_text(
        'henxels:\n  - henxel: "Mine"\n    required_files: README.md\n', encoding="utf-8"
    )
    report = init(tmp_path, install_git_hooks=False, template=TEMPLATE)
    assert report["contract"][0] == "exists"
    assert "Mine" in _read(tmp_path, "henxels.yaml")
    assert "_brain" in report["fragment"]
    assert not (tmp_path / "_brain").exists()


# --- CLI ---------------------------------------------------------------------

def test_cli_scaffold_reports_template_and_next_step(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--template", TEMPLATE, "--no-hooks"]) == 0
    out = capsys.readouterr().out
    assert TEMPLATE in out
    assert "_brain" in out
    assert "brainpick init" in out  # the handoff: henxels scaffolds, brainpick serves
