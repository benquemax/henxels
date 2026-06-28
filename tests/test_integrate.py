"""`henxels integrate <harness>` materializes a packaged integration into the project."""

from pathlib import Path

import pytest

from henxels.integrate import available, write_integration


def test_write_opencode(tmp_path):
    path, action = write_integration("opencode", tmp_path)
    assert action == "created"
    assert path == tmp_path / ".opencode" / "plugins" / "henxels.js"
    text = path.read_text(encoding="utf-8")
    assert "tool.execute.before" in text and "ask_me_before_staging" in text


def test_idempotent_reports_updated(tmp_path):
    write_integration("opencode", tmp_path)
    _, action = write_integration("opencode", tmp_path)
    assert action == "updated"


def test_unknown_harness(tmp_path):
    with pytest.raises(ValueError):
        write_integration("nope", tmp_path)
    assert "opencode" in available()


def test_packaged_matches_reference():
    # the packaged plugin and the browsable reference in integrations/ must not drift
    repo = Path(__file__).resolve().parent.parent
    packaged = (repo / "henxels" / "integrations" / "opencode.js").read_text(encoding="utf-8")
    reference = (repo / "integrations" / "opencode" / "henxels.js").read_text(encoding="utf-8")
    assert packaged == reference
