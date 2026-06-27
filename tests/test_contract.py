"""v2 contract loading + custom-statement imports (explicit and auto-discovered)."""

from henxels.contract import apply_imports, load_contract
from henxels.statements.registry import get_statement


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_load_settings_and_henxels(tmp_path):
    p = _write(
        tmp_path,
        "henxels.yaml",
        """
settings:
  confirm_before_push: true
henxels:
  - henxel: "Docs are kebab-case"
    in: docs
    casing: kebab-case
  - rule: "Two locations"
    in: [a, b]
    level: warn
    forbidden_files: x.py
""",
    )
    c = load_contract(p)
    assert c.settings["confirm_before_push"] is True
    assert len(c.henxels) == 2
    h0 = c.henxels[0]
    assert h0.text == "Docs are kebab-case"
    assert h0.locations == ["docs"]
    assert h0.statements == {"casing": "kebab-case"}
    h1 = c.henxels[1]
    assert h1.text == "Two locations"  # `rule:` alias accepted
    assert h1.locations == ["a", "b"]
    assert h1.level == "warn"
    assert h1.statements == {"forbidden_files": "x.py"}


def test_in_root_default(tmp_path):
    p = _write(tmp_path, "henxels.yaml", 'henxels:\n  - henxel: "x"\n    required_files: _todo.md\n')
    c = load_contract(p)
    assert c.henxels[0].locations == ["./*"]  # no `in:` = whole repo


def test_except_excludes_parsed(tmp_path):
    p = _write(
        tmp_path,
        "henxels.yaml",
        """
henxels:
  - henxel: "Pages only"
    in: ./*
    except: [./raw/*, index.md]
    filename_casing: kebab-case
""",
    )
    c = load_contract(p)
    h = c.henxels[0]
    assert h.excludes == ["./raw/*", "index.md"]
    assert "except" not in h.statements  # reserved, not a statement


def test_except_absent_is_empty(tmp_path):
    p = _write(tmp_path, "henxels.yaml", 'henxels:\n  - henxel: "x"\n    required_files: a.md\n')
    c = load_contract(p)
    assert c.henxels[0].excludes == []


def test_explicit_import(tmp_path):
    _write(
        tmp_path,
        "mychecks.py",
        "from henxels import statement\n"
        "@statement('imported_demo')\n"
        "def demo(scope):\n"
        "    return None\n",
    )
    p = _write(tmp_path, "henxels.yaml", 'imports:\n  - mychecks.py\nhenxels: []\n')
    c = load_contract(p)
    assert apply_imports(c, root=tmp_path) == []
    assert get_statement("imported_demo") is not None


def test_auto_discovered_local_checks(tmp_path):
    _write(
        tmp_path,
        "henxels_checks.py",
        "from henxels import statement\n"
        "@statement('auto_demo')\n"
        "def demo(scope):\n"
        "    return None\n",
    )
    p = _write(tmp_path, "henxels.yaml", "henxels: []\n")
    c = load_contract(p)
    apply_imports(c, root=tmp_path)  # no imports: needed
    assert get_statement("auto_demo") is not None
