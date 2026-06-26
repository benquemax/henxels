"""Opt-in plugins: frontmatter (dependency-free) and markdown gating."""

from henxels.config.load import Config
from henxels.plugins import run_plugins
from henxels.plugins.frontmatter import check_frontmatter

FM_CONFIG = Config(plugins={"frontmatter": {"docs": ["title", "date"]}})


def _md(tmp_path, rel, body):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return rel


def test_frontmatter_missing_key_blocks(tmp_path):
    rel = _md(tmp_path, "docs/intro.md", "---\ntitle: Hi\n---\n\n# Hi\n")
    findings = check_frontmatter(FM_CONFIG, tmp_path, [rel])
    assert len(findings) == 1
    assert findings[0].henxel == "frontmatter"
    assert "date" in findings[0].message


def test_frontmatter_all_present_ok(tmp_path):
    rel = _md(tmp_path, "docs/intro.md", "---\ntitle: Hi\ndate: 2026-01-01\n---\n\n# Hi\n")
    assert check_frontmatter(FM_CONFIG, tmp_path, [rel]) == []


def test_frontmatter_no_block_at_all(tmp_path):
    rel = _md(tmp_path, "docs/intro.md", "# Hi, no frontmatter\n")
    findings = check_frontmatter(FM_CONFIG, tmp_path, [rel])
    assert len(findings) == 2  # both title and date missing


def test_frontmatter_only_governed_folders(tmp_path):
    rel = _md(tmp_path, "blog/post.md", "# no rules here\n")
    assert check_frontmatter(FM_CONFIG, tmp_path, [rel]) == []


def test_plugins_off_by_default(tmp_path):
    rel = _md(tmp_path, "docs/intro.md", "# nothing\n")
    assert run_plugins(Config(), tmp_path, [rel]) == []
