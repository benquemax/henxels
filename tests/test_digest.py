"""Digest rendering and the managed-block round-trip."""

from henxels.config.load import Config
from henxels.digest import BEGIN, END, render_digest, sync_file, update_block

CFG = Config(
    guards={"push": "bless", "delete": {"mode": "bless", "line_threshold": 5}, "stage": "ask"},
    canonical=[{"role": "project config", "file": "pyproject.toml", "forbid_lookalikes": ["setup.py"]}],
    require=[{"file": "_temp/.gitkeep", "reason": "scratch folder"}, {"file": "_todo.md", "severity": "warn"}],
    checks={"pre_commit": ["uv run pytest -q"]},
    tree={
        "src": {
            "naming": "snake_case",
            "forbid": [{"glob": "**/*_test.py", "reason": "tests live in tests/", "steer": "use tests/"}],
            "api": {"require": [{"file": "handlers.py", "reason": "expose handlers"}]},
        },
        "tests": {"naming": "snake_case", "mirror": "src/**"},
    },
)


def test_render_digest_has_key_facts():
    d = render_digest(CFG)
    assert "closest rule in the tree wins" in d
    assert "`src/`" in d
    assert "files are snake_case" in d
    assert "forbid `**/*_test.py`" in d
    assert "must contain `handlers.py`" in d
    assert "mirrors `src/**`" in d
    assert "bless push" in d
    assert "bless delete" in d
    assert "ask the user first" in d
    assert "pyproject.toml" in d
    assert "_temp/.gitkeep" in d
    assert "_todo.md" in d and "_(warn)_" in d
    assert "uv run pytest -q" in d


def test_update_block_appends_when_absent():
    out = update_block("# My Project\n\nNotes.\n", "DIGEST")
    assert BEGIN in out and END in out
    assert out.startswith("# My Project")
    assert "DIGEST" in out


def test_update_block_replaces_and_preserves_surroundings():
    original = f"top\n\n{BEGIN}\nOLD\n{END}\n\nbottom\n"
    out = update_block(original, "NEW")
    assert "OLD" not in out
    assert "NEW" in out
    assert out.startswith("top")
    assert out.rstrip().endswith("bottom")


def test_sync_file_create_then_update(tmp_path):
    target = tmp_path / "AGENTS.md"
    assert sync_file(target, CFG) == "created"
    first = target.read_text()
    assert BEGIN in first

    # Human edits outside the block survive a re-sync.
    target.write_text(first + "\n## My own notes\nkeep me\n", encoding="utf-8")
    assert sync_file(target, CFG) == "updated"
    after = target.read_text()
    assert "keep me" in after
    assert after.count(BEGIN) == 1  # not duplicated
