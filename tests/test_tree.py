"""Closest-rule-in-tree resolution."""

from henxels.config.tree import resolve

TREE = {
    "src": {
        "naming": "snake_case",
        "forbid": [
            {
                "glob": "**/*_test.py",
                "reason": "tests live in tests/",
                "steer": "mirror the path under tests/",
            }
        ],
        "api": {
            "require": [{"file": "handlers.py", "reason": "every api module exposes handlers"}],
        },
        "ui": {
            "naming": "kebab-case",
        },
    },
    "tests": {
        "naming": "snake_case",
        "mirror": "src/**",
    },
    "docs": {
        "naming": "kebab-case",
    },
}


def test_naming_cascades_down():
    r = resolve(TREE, "src/api/handlers.py")
    assert r.naming == "snake_case"


def test_closest_naming_wins():
    r = resolve(TREE, "src/ui/button.py")
    assert r.naming == "kebab-case"  # ui overrides src


def test_forbid_accumulates_and_matches():
    r = resolve(TREE, "src/api/thing_test.py")
    assert r.matched_forbid is not None
    assert r.matched_forbid.reason == "tests live in tests/"
    assert r.matched_forbid.node == "src"


def test_forbid_present_but_not_violated():
    r = resolve(TREE, "src/api/handlers.py")
    assert any(f.glob == "**/*_test.py" for f in r.forbid)
    assert r.matched_forbid is None


def test_require_belongs_to_folder_node():
    r = resolve(TREE, "src/api/handlers.py")
    assert r.node_path == "src/api"
    assert r.require and r.require[0]["file"] == "handlers.py"


def test_mirror_read_from_deepest_node():
    r = resolve(TREE, "tests/api/thing.py")
    assert r.mirror == "src/**"


def test_unknown_path_has_no_rules():
    r = resolve(TREE, "random/place/file.py")
    assert r.naming is None
    assert r.forbid == []
    assert r.matched_forbid is None


def test_root_file_has_no_dir_rules():
    r = resolve(TREE, "README.md")
    assert r.naming is None
    assert r.node_path == ""
