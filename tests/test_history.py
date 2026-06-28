"""Git-diff-aware statements: append_only, immutable, bump_updated_on_change."""

import subprocess

from henxels.diffinfo import staged_diff
from henxels.statements.builtins.history import (
    append_only,
    bump_updated_on_change,
    changed_with,
    immutable,
)
from henxels.statements.scope import build_scope


def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)


def _repo(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    return tmp_path


def _write(root, rel, content):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _commit(root, rel, content):
    _write(root, rel, content)
    _git(root, "add", rel)
    _git(root, "commit", "-qm", "seed")


def _stage(root, rel, content):
    _write(root, rel, content)
    _git(root, "add", rel)


def _scope(root, files):
    return build_scope(["./*"], files, root, {})


# --- append_only ---------------------------------------------------------

def test_append_only_blocks_edit(tmp_path):
    r = _repo(tmp_path)
    _commit(r, "log.md", "a\nb\n")
    _stage(r, "log.md", "a\nX\n")  # changed an existing line
    assert append_only(True, _scope(r, ["log.md"]), staged_diff(r))


def test_append_only_allows_append(tmp_path):
    r = _repo(tmp_path)
    _commit(r, "log.md", "a\nb\n")
    _stage(r, "log.md", "a\nb\nc\n")  # pure append
    assert append_only(True, _scope(r, ["log.md"]), staged_diff(r)) == []


# --- immutable -----------------------------------------------------------

def test_immutable_blocks_modify(tmp_path):
    r = _repo(tmp_path)
    _commit(r, "raw/a.md", "orig\n")
    _stage(r, "raw/a.md", "changed\n")
    assert immutable(True, _scope(r, ["raw/a.md"]), staged_diff(r))


def test_immutable_allows_new_file(tmp_path):
    r = _repo(tmp_path)
    _commit(r, "raw/a.md", "orig\n")
    _stage(r, "raw/b.md", "new\n")  # added, not modified
    assert immutable(True, _scope(r, ["raw/a.md", "raw/b.md"]), staged_diff(r)) == []


# --- bump_updated_on_change ----------------------------------------------

def test_bump_updated_required_when_body_changes(tmp_path):
    r = _repo(tmp_path)
    _commit(r, "p.md", "---\nupdated: 2026-06-01\n---\nbody\n")
    _stage(r, "p.md", "---\nupdated: 2026-06-01\n---\nbody changed\n")  # forgot to bump
    assert bump_updated_on_change("updated", _scope(r, ["p.md"]), staged_diff(r))


def test_bump_updated_satisfied(tmp_path):
    r = _repo(tmp_path)
    _commit(r, "p.md", "---\nupdated: 2026-06-01\n---\nbody\n")
    _stage(r, "p.md", "---\nupdated: 2026-06-02\n---\nbody changed\n")
    assert bump_updated_on_change("updated", _scope(r, ["p.md"]), staged_diff(r)) == []


# --- changed_with (commit-time companion reminder) -----------------------

def test_changed_with_warns_when_companion_missing(tmp_path):
    r = _repo(tmp_path)
    _commit(r, "code.py", "x\n")
    _commit(r, "docs/d.md", "x\n")
    _stage(r, "code.py", "y\n")  # changed code, but not docs
    assert changed_with({"when": "code.py", "expect": "docs/*"}, staged_diff(r))


def test_changed_with_satisfied_when_companion_changes(tmp_path):
    r = _repo(tmp_path)
    _commit(r, "code.py", "x\n")
    _commit(r, "docs/d.md", "x\n")
    _stage(r, "code.py", "y\n")
    _stage(r, "docs/d.md", "y\n")  # both changed → no reminder
    assert changed_with({"when": "code.py", "expect": "docs/*"}, staged_diff(r)) is None


def test_changed_with_quiet_when_trigger_untouched(tmp_path):
    r = _repo(tmp_path)
    _commit(r, "code.py", "x\n")
    _commit(r, "docs/d.md", "x\n")
    _stage(r, "docs/d.md", "y\n")  # only docs changed; trigger not touched
    assert changed_with({"when": "code.py", "expect": "docs/*"}, staged_diff(r)) is None


# --- no diff (e.g. check --all) → every history statement passes ----------

def test_no_diff_is_noop(tmp_path):
    s = build_scope(["./*"], [], tmp_path, {})
    assert append_only(True, s, None) == []
    assert immutable(True, s, None) == []
    assert bump_updated_on_change("updated", s, None) == []
    assert changed_with({"when": "a", "expect": "b"}, None) is None
