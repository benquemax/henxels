"""The repo's local schema copy must not silently outlive the installed henxels.

`henxels init` writes `.henxels/henxels.schema.json` so editors autocomplete offline.
But init is the ONLY thing that refreshed it: after `uv tool upgrade henxels`, a repo
kept the schema of the version it was init'd with, and nothing said so. A contract key
the tool fully supported (e.g. `budget`) looked unsupported to anyone — human or agent —
reading the committed artifact. That is the "stale schema" nag, distinct from the
existing "stale tool" nag: the tool is current, the repo's copy of its documentation
is not.
"""

import json

from henxels.schema import (
    LOCAL_SCHEMA_PATH,
    local_schema_state,
    refresh_local_schema,
    schema_text,
)


def _write_local(root, text):
    path = root / LOCAL_SCHEMA_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --- state detection --------------------------------------------------------

def test_state_missing_when_never_written(tmp_path):
    # A repo that doesn't keep a local copy is a legitimate choice, not drift.
    assert local_schema_state(tmp_path) == "missing"


def test_state_fresh_when_it_matches_the_bundled_schema(tmp_path):
    _write_local(tmp_path, schema_text())
    assert local_schema_state(tmp_path) == "fresh"


def test_state_stale_when_the_tool_moved_on(tmp_path):
    # Exactly the 0.14.0 situation: an older schema, missing a key the tool supports.
    old = json.loads(schema_text())
    old["properties"].pop("requires_henxels", None)
    _write_local(tmp_path, json.dumps(old, indent=2) + "\n")
    assert local_schema_state(tmp_path) == "stale"


def test_state_ignores_trailing_whitespace_only_differences(tmp_path):
    # Line-ending churn (a Windows checkout, an editor's final-newline setting) is not
    # a stale schema; nagging about it would train people to ignore the nag.
    _write_local(tmp_path, schema_text().rstrip() + "\n\n")
    assert local_schema_state(tmp_path) == "fresh"


def test_state_stale_when_the_copy_is_corrupt(tmp_path):
    _write_local(tmp_path, "{not json at all")
    assert local_schema_state(tmp_path) == "stale"


# --- refreshing -------------------------------------------------------------

def test_refresh_writes_the_bundled_schema_and_reports(tmp_path):
    _write_local(tmp_path, "{}")
    assert refresh_local_schema(tmp_path) == "updated"
    assert local_schema_state(tmp_path) == "fresh"


def test_refresh_creates_when_absent(tmp_path):
    assert refresh_local_schema(tmp_path) == "created"
    assert (tmp_path / LOCAL_SCHEMA_PATH).is_file()


def test_refresh_is_idempotent_and_says_unchanged(tmp_path):
    refresh_local_schema(tmp_path)
    # "unchanged" matters: sync must not dirty the worktree on every run, or the
    # maintainer sees a spurious diff to stage each time.
    assert refresh_local_schema(tmp_path) == "unchanged"


# --- `henxels sync` refreshes it -------------------------------------------

def _seed_contract(root):
    (root / "henxels.yaml").write_text(
        'henxels:\n  - henxel: "Docs are kebab-case"\n    in: ./docs\n    filename_casing: kebab-case\n',
        encoding="utf-8",
    )


def test_sync_refreshes_a_stale_local_schema(tmp_path, monkeypatch, capsys):
    from henxels.cli import main

    _seed_contract(tmp_path)
    _write_local(tmp_path, "{}")
    monkeypatch.chdir(tmp_path)

    assert main(["sync"]) == 0
    out = capsys.readouterr().out
    # sync was the gap: it refreshed the digest but left the schema behind, so the
    # only cure was remembering to re-run init. Now sync closes the loop.
    assert local_schema_state(tmp_path) == "fresh"
    assert ".henxels/henxels.schema.json" in out


def test_sync_leaves_a_repo_without_a_local_copy_alone(tmp_path, monkeypatch):
    from henxels.cli import main

    _seed_contract(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert main(["sync"]) == 0
    # Never conjure the file into a repo that deliberately doesn't keep one — that
    # would be sync inventing a new committed artifact behind the user's back.
    assert local_schema_state(tmp_path) == "missing"


def test_sync_check_reports_stale_schema_without_writing(tmp_path, monkeypatch, capsys):
    from henxels.cli import main
    from henxels.contract import load_contract
    from henxels.digest import sync_file

    _seed_contract(tmp_path)
    sync_file(tmp_path / "AGENTS.md", load_contract(tmp_path / "henxels.yaml"))
    _write_local(tmp_path, "{}")
    monkeypatch.chdir(tmp_path)

    code = main(["sync", "--check"])
    assert code == 1  # drift is drift, even when the digest itself is fresh
    err = capsys.readouterr().err
    assert "schema" in err.lower()
    assert local_schema_state(tmp_path) == "stale"  # --check never writes


# --- the pre-commit nag -----------------------------------------------------

def test_precommit_warns_about_a_stale_schema(git_repo):
    from henxels.hookrun import run_precommit

    _seed_contract(git_repo)
    _write_local(git_repo, "{}")
    code, findings = run_precommit(git_repo)

    stale = [f for f in findings if "schema" in f.message.lower()]
    assert stale, [f.message for f in findings]
    assert code == 0                       # a nag, never a block
    assert not stale[0].is_block
    assert "henxels init" in (stale[0].steer or "")


def test_precommit_silent_when_the_schema_is_current(git_repo):
    from henxels.hookrun import run_precommit

    _seed_contract(git_repo)
    _write_local(git_repo, schema_text())
    _, findings = run_precommit(git_repo)
    assert not [f for f in findings if "schema" in f.message.lower()]


def test_precommit_silent_when_there_is_no_local_copy(git_repo):
    from henxels.hookrun import run_precommit

    _seed_contract(git_repo)
    _, findings = run_precommit(git_repo)
    assert not [f for f in findings if "schema" in f.message.lower()]


# --- doctor -----------------------------------------------------------------

def test_doctor_flags_a_stale_local_schema(git_repo):
    from henxels.doctor import diagnose

    _seed_contract(git_repo)
    _write_local(git_repo, "{}")
    check = next(c for c in diagnose(git_repo) if "schema" in c.label)
    assert not check.ok
    assert "init" in check.detail


def test_doctor_green_when_schema_is_fresh(git_repo):
    from henxels.doctor import diagnose

    _seed_contract(git_repo)
    _write_local(git_repo, schema_text())
    check = next(c for c in diagnose(git_repo) if "schema" in c.label)
    assert check.ok

