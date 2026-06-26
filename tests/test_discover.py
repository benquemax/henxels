"""File discovery (filesystem-walk mode)."""

from henxels.engine.discover import discover


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")


def test_discover_walks_and_excludes(tmp_path):
    _touch(tmp_path / "README.md")
    _touch(tmp_path / "src" / "app.py")
    _touch(tmp_path / "node_modules" / "dep" / "index.js")
    _touch(tmp_path / "__pycache__" / "x.pyc")
    _touch(tmp_path / "_temp" / "scratch.txt")

    found = discover(tmp_path, use_git=False)

    assert "README.md" in found
    assert "src/app.py" in found
    assert not any("node_modules" in p for p in found)
    assert not any("__pycache__" in p for p in found)
    assert not any(p.startswith("_temp/") for p in found)


def test_discover_custom_excludes(tmp_path):
    _touch(tmp_path / "keep.py")
    _touch(tmp_path / "vendor" / "x.py")
    found = discover(tmp_path, excludes={"vendor"}, use_git=False)
    assert "keep.py" in found
    assert not any("vendor" in p for p in found)


def test_discover_sorted(tmp_path):
    _touch(tmp_path / "b.md")
    _touch(tmp_path / "a.md")
    found = discover(tmp_path, use_git=False)
    assert found == sorted(found)
