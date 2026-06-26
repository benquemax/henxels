"""Root-level require + per-require severity."""

from henxels.config.load import Config, load_config
from henxels.rules.existence import check_root_required


def test_root_require_missing_blocks(tmp_path):
    findings = check_root_required([{"file": "_todo.md"}], tmp_path)
    assert len(findings) == 1
    assert findings[0].is_block
    assert findings[0].henxel == "require"
    assert "_todo.md" in findings[0].path


def test_root_require_present_ok(tmp_path):
    (tmp_path / "_todo.md").write_text("x", encoding="utf-8")
    assert check_root_required([{"file": "_todo.md"}], tmp_path) == []


def test_root_require_folder_via_gitkeep(tmp_path):
    findings = check_root_required([{"file": "_temp/.gitkeep"}], tmp_path)
    assert findings and findings[0].is_block
    (tmp_path / "_temp").mkdir()
    (tmp_path / "_temp" / ".gitkeep").write_text("", encoding="utf-8")
    assert check_root_required([{"file": "_temp/.gitkeep"}], tmp_path) == []


def test_severity_warn_does_not_block(tmp_path):
    findings = check_root_required(
        [{"file": "_todo.md", "severity": "warn", "reason": "gitignored"}], tmp_path
    )
    assert len(findings) == 1
    assert not findings[0].is_block  # warning, survives CI


def test_loader_parses_require_and_checks(tmp_path):
    p = tmp_path / "henxels.yaml"
    p.write_text(
        """
henxels: 1
require:
  - file: _todo.md
    severity: warn
checks:
  pre_commit:
    - "echo hi"
""",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.require[0]["file"] == "_todo.md"
    assert cfg.checks["pre_commit"] == ["echo hi"]
