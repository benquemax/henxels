"""Canonical single-source / forbidden look-alikes."""

from henxels.config.load import Config
from henxels.rules.duplication import check_canonical


def test_lookalike_basename_blocked():
    cfg = Config(
        canonical=[{"role": "project config", "file": "pyproject.toml", "forbid_lookalikes": ["setup.py"]}]
    )
    findings = check_canonical(cfg, ["pyproject.toml", "setup.py"])
    assert len(findings) == 1
    assert findings[0].henxel == "canonical"
    assert "pyproject.toml" in findings[0].steer


def test_lookalike_basename_matches_anywhere():
    cfg = Config(canonical=[{"file": "pyproject.toml", "forbid_lookalikes": ["setup.py"]}])
    findings = check_canonical(cfg, ["nested/dir/setup.py"])
    assert len(findings) == 1


def test_lookalike_glob_blocked():
    cfg = Config(canonical=[{"file": "config.py", "forbid_lookalikes": ["**/settings.py"]}])
    findings = check_canonical(cfg, ["app/settings.py"])
    assert len(findings) == 1


def test_canonical_home_itself_not_flagged():
    cfg = Config(canonical=[{"file": "pyproject.toml", "forbid_lookalikes": ["pyproject.toml"]}])
    assert check_canonical(cfg, ["pyproject.toml"]) == []


def test_no_canonical_no_findings():
    assert check_canonical(Config(), ["whatever.py"]) == []
