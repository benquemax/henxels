"""Contract loading and light validation."""

import pytest

from henxels.config.load import (
    Config,
    ConfigError,
    SUPPORTED_VERSION,
    find_config,
    load_config,
)


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_find_config_prefers_henxels_yaml(tmp_path):
    _write(tmp_path, "henxels.yaml", "henxels: 1\n")
    _write(tmp_path, ".henxels.yaml", "henxels: 1\n")
    assert find_config(tmp_path).name == "henxels.yaml"


def test_find_config_absent(tmp_path):
    assert find_config(tmp_path) is None


def test_load_minimal(tmp_path):
    p = _write(tmp_path, "henxels.yaml", "henxels: 1\n")
    cfg = load_config(p)
    assert isinstance(cfg, Config)
    assert cfg.version == 1
    assert cfg.tree == {}
    assert cfg.path == p


def test_load_full_shape(tmp_path):
    p = _write(
        tmp_path,
        "henxels.yaml",
        """
henxels: 1
guards:
  push: bless
similarity:
  warn_above: 0.85
  exclude: ["**/__init__.py"]
canonical:
  - role: "project config"
    file: pyproject.toml
tree:
  src:
    naming: snake_case
""",
    )
    cfg = load_config(p)
    assert cfg.guards == {"push": "bless"}
    assert cfg.similarity["warn_above"] == 0.85
    assert cfg.canonical[0]["file"] == "pyproject.toml"
    assert cfg.tree["src"]["naming"] == "snake_case"


def test_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nope.yaml")


def test_non_mapping_raises(tmp_path):
    p = _write(tmp_path, "henxels.yaml", "- just\n- a\n- list\n")
    with pytest.raises(ConfigError):
        load_config(p)


def test_future_version_rejected(tmp_path):
    p = _write(tmp_path, "henxels.yaml", f"henxels: {SUPPORTED_VERSION + 1}\n")
    with pytest.raises(ConfigError):
        load_config(p)
