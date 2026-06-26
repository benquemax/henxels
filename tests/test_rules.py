"""Rule types: placement, naming, existence — and the checker that runs them."""

from henxels.config.load import Config
from henxels.config.tree import resolve
from henxels.checker import check_paths
from henxels.rules.naming import check_naming
from henxels.rules.placement import check_placement

TREE = {
    "src": {
        "naming": "snake_case",
        "forbid": [
            {"glob": "**/*_test.py", "reason": "tests live in tests/", "steer": "use tests/"}
        ],
        "api": {"require": [{"file": "handlers.py", "reason": "expose handlers"}]},
        "ui": {"naming": "kebab-case"},
    },
}


def test_placement_blocks_forbidden_file():
    findings = check_placement(resolve(TREE, "src/api/thing_test.py"))
    assert len(findings) == 1
    f = findings[0]
    assert f.is_block
    assert f.henxel == "placement"
    assert f.reason == "tests live in tests/"
    assert f.steer == "use tests/"


def test_placement_allows_ok_file():
    assert check_placement(resolve(TREE, "src/api/handlers.py")) == []


def test_naming_blocks_wrong_case():
    findings = check_naming(resolve(TREE, "src/myModule.py"))
    assert len(findings) == 1
    assert findings[0].henxel == "naming"
    assert "snake_case" in findings[0].steer


def test_naming_allows_right_case():
    assert check_naming(resolve(TREE, "src/my_module.py")) == []


def test_naming_closest_wins():
    # ui requires kebab-case; snake-cased name should fail there
    findings = check_naming(resolve(TREE, "src/ui/my_button.py"))
    assert findings and "kebab-case" in findings[0].steer


def test_naming_multi_extension_uses_base():
    # judged on "button", not "button.test"
    assert check_naming(resolve(TREE, "src/ui/button.test.js")) == []


def test_naming_skips_dunder_files():
    # __init__.py / __main__.py are language-mandated, not style choices
    assert check_naming(resolve(TREE, "src/__init__.py")) == []
    assert check_naming(resolve(TREE, "src/api/__main__.py")) == []


def test_unknown_convention_flagged():
    findings = check_naming(resolve({"x": {"naming": "bogus"}}, "x/file.py"))
    assert findings and "unknown naming convention" in findings[0].message


def test_existence_missing_required_file(tmp_path):
    (tmp_path / "src" / "api").mkdir(parents=True)
    cfg = Config(tree=TREE)
    findings = check_paths(cfg, tmp_path, [], check_existence=True)
    assert any(f.henxel == "require" and "handlers.py" in f.path for f in findings)


def test_existence_present_required_file(tmp_path):
    api = tmp_path / "src" / "api"
    api.mkdir(parents=True)
    (api / "handlers.py").write_text("x", encoding="utf-8")
    cfg = Config(tree=TREE)
    findings = check_paths(cfg, tmp_path, [], check_existence=True)
    assert not any(f.henxel == "require" for f in findings)


def test_existence_skipped_when_folder_absent(tmp_path):
    cfg = Config(tree=TREE)
    findings = check_paths(cfg, tmp_path, [], check_existence=True)
    assert not any(f.henxel == "require" for f in findings)


def test_check_paths_partial_skips_existence(tmp_path):
    cfg = Config(tree=TREE)
    findings = check_paths(
        cfg, tmp_path, ["src/api/thing_test.py"], check_existence=False
    )
    assert all(f.henxel != "require" for f in findings)
    assert any(f.henxel == "placement" for f in findings)
