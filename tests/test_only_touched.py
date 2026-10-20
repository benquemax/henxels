"""`only_touched: true` — a henxel that applies only to files a commit touches."""

import subprocess

from henxels.contract import load_contract
from henxels.digest import render_digest
from henxels.explain import explain_path
from henxels.hookrun import run_precommit
from henxels.runner import run_contract

YAML = """
henxels:
  - henxel: "Notes are kebab-case"
    in: ./notes
    level: warn
    only_touched: true
    filename_casing: kebab-case
"""


def _git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)


def _contract(root, text=YAML):
    (root / "henxels.yaml").write_text(text, encoding="utf-8")
    return load_contract(root / "henxels.yaml")


def _seed(root):
    (root / "notes").mkdir()
    (root / "notes/Old_Bad.md").write_text("x", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "seed")


def test_parsing_defaults_and_reserved(tmp_path):
    c = _contract(tmp_path)
    assert c.henxels[0].only_touched is True
    assert "only_touched" not in c.henxels[0].statements
    c = _contract(tmp_path, YAML.replace("    only_touched: true\n", ""))
    assert c.henxels[0].only_touched is False


def test_runner_filters_to_touched_only(tmp_path):
    c = _contract(tmp_path)
    files = ["notes/Old_Bad.md", "notes/New_Bad.md"]
    for f in files:
        (tmp_path / f).parent.mkdir(exist_ok=True)
        (tmp_path / f).write_text("x", encoding="utf-8")
    out = run_contract(c, tmp_path, files, touched=["notes/New_Bad.md"])
    text = "\n".join(d for f in out for d in f.details)
    assert "New_Bad" in text and "Old_Bad" not in text
    # nothing touched in scope -> per-file statements have nothing to check
    assert run_contract(c, tmp_path, files, touched=["other.txt"]) == []
    # touched=None (check --all / paths): whole repo
    text = "\n".join(d for f in run_contract(c, tmp_path, files) for d in f.details)
    assert "New_Bad" in text and "Old_Bad" in text


def test_non_only_touched_henxel_unaffected(tmp_path):
    c = _contract(tmp_path, YAML.replace("    only_touched: true\n", ""))
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes/Old_Bad.md").write_text("x", encoding="utf-8")
    out = run_contract(c, tmp_path, ["notes/Old_Bad.md"], touched=["other.txt"])
    assert len(out) == 1


def test_precommit_reports_staged_not_unstaged(git_repo):
    _contract(git_repo)
    _seed(git_repo)
    (git_repo / "notes/New_Bad.md").write_text("y", encoding="utf-8")
    _git(git_repo, "add", "notes/New_Bad.md")
    _, findings = run_precommit(git_repo)
    text = "\n".join(d for f in findings for d in f.details)
    assert "New_Bad" in text and "Old_Bad" not in text


def test_precommit_rename_counts_new_path_only(git_repo):
    _contract(git_repo)
    _seed(git_repo)
    _git(git_repo, "mv", "notes/Old_Bad.md", "notes/New_Bad.md")
    _, findings = run_precommit(git_repo)
    text = "\n".join(d for f in findings for d in f.details)
    assert "New_Bad" in text and "Old_Bad" not in text


def test_digest_and_explain_tag(tmp_path):
    c = _contract(tmp_path)
    assert "_(warn)_ _(on touch)_" in render_digest(c)
    assert "[on touch]" in explain_path(c, "notes/a.md")


def test_digest_legend_only_when_used(tmp_path):
    legend = "A rule tagged _(on touch)_"
    assert legend in render_digest(_contract(tmp_path))
    assert legend not in render_digest(_contract(tmp_path, YAML.replace("    only_touched: true\n", "")))


def test_folder_level_statement_still_sees_whole_folder(git_repo):
    _contract(git_repo, """
henxels:
  - henxel: "Notes have an index"
    in: ./notes
    only_touched: true
    required_files: [index.md]
""")
    (git_repo / "notes").mkdir()
    (git_repo / "notes/index.md").write_text("x", encoding="utf-8")
    (git_repo / "notes/a.md").write_text("x", encoding="utf-8")
    _git(git_repo, "add", ".")
    _git(git_repo, "commit", "-q", "-m", "seed")
    _git(git_repo, "rm", "-q", "notes/index.md")
    _, findings = run_precommit(git_repo)
    assert any("Notes have an index" == f.henxel for f in findings)


def test_max_files_sees_whole_folder(tmp_path):
    c = _contract(tmp_path, YAML.replace("filename_casing: kebab-case", "max_files: 1"))
    files = ["notes/a.md", "notes/b.md"]
    for f in files:
        (tmp_path / f).parent.mkdir(exist_ok=True)
        (tmp_path / f).write_text("x", encoding="utf-8")
    assert run_contract(c, tmp_path, files, touched=["notes/a.md"])


def test_contract_below_git_toplevel(git_repo):
    sub = git_repo / "sub"
    (sub / "notes").mkdir(parents=True)
    _contract(sub)
    (sub / "notes/New_Bad.md").write_text("y", encoding="utf-8")
    _git(git_repo, "add", "sub/notes/New_Bad.md")
    _, findings = run_precommit(sub)
    assert "New_Bad" in "\n".join(d for f in findings for d in f.details)


def _cli_repo(git_repo, monkeypatch):
    _contract(git_repo)
    _seed(git_repo)
    (git_repo / "notes/New_Bad.md").write_text("y", encoding="utf-8")
    _git(git_repo, "add", "notes/New_Bad.md")
    monkeypatch.chdir(git_repo)


def test_cli_check_staged_vs_all(git_repo, monkeypatch, capsys):
    from henxels.cli import main

    _cli_repo(git_repo, monkeypatch)
    for argv in (["check", "--plain"], ["check", "--staged", "--plain"]):
        main(argv)
        out = capsys.readouterr().out
        assert "New_Bad" in out and "Old_Bad" not in out
    main(["check", "--all", "--plain"])
    out = capsys.readouterr().out
    assert "New_Bad" in out and "Old_Bad" in out


def test_non_ascii_staged_path_is_checked(git_repo):
    # git quotes non-ASCII paths by default ("notes/\303\204iti.md"); unquoted they match scope.
    _contract(git_repo)
    (git_repo / "notes").mkdir(exist_ok=True)
    (git_repo / "notes/Äiti_Bad.md").write_text("y", encoding="utf-8")
    _git(git_repo, "add", "notes/Äiti_Bad.md")
    _, findings = run_precommit(git_repo)
    assert "Äiti_Bad" in "\n".join(d for f in findings for d in f.details)
