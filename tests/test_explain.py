"""`henxels explain` — plain-language contract for a path."""

from henxels.config.load import Config
from henxels.explain import explain_path

TREE = {
    "src": {
        "naming": "snake_case",
        "forbid": [{"glob": "**/*_test.py", "reason": "tests live in tests/", "steer": "use tests/"}],
        "api": {"require": [{"file": "handlers.py", "reason": "expose handlers"}]},
    },
}


def test_explain_forbidden_path():
    out = explain_path(Config(tree=TREE), "src/api/foo_test.py")
    assert "FORBIDDEN" in out
    assert "tests live in tests/" in out
    assert "use tests/" in out


def test_explain_normal_path_lists_rules():
    out = explain_path(Config(tree=TREE), "src/api/handlers.py")
    assert "naming: files here are snake_case" in out
    assert "this folder must contain:" in out
    assert "handlers.py" in out
    assert "FORBIDDEN" not in out


def test_explain_silent_location():
    out = explain_path(Config(tree=TREE), "random/file.py")
    assert "no henxels apply" in out
