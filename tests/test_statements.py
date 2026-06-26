"""Built-in statement vocabulary + scalar-or-list / OR / AND / none-of semantics."""

from henxels.statements.registry import get_statement
from henxels.statements.scope import build_scope


def scope_for(tmp_path, files, locations=None):
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return build_scope(locations or ["./*"], list(files), tmp_path, {})


def run(name, param, scope):
    return get_statement(name).fn(param, scope)


# --- casing (MATCH: scalar, and list = OR) -------------------------------

def test_casing_scalar_pass(tmp_path):
    assert run("filename_casing", "snake_case", scope_for(tmp_path, {"my_mod.py": "x"})) == []


def test_casing_scalar_fail(tmp_path):
    assert run("filename_casing", "snake_case", scope_for(tmp_path, {"BadName.py": "x"}))


def test_casing_list_is_or(tmp_path):
    s = scope_for(tmp_path, {"a-b.md": "x"})
    assert run("filename_casing", ["snake_case", "kebab-case"], s) == []


def test_casing_skips_dunder(tmp_path):
    assert run("filename_casing", "snake_case", scope_for(tmp_path, {"__init__.py": "x"})) == []


# --- files_are (MATCH: extension or glob, list = OR) ---------------------

def test_files_are_extension(tmp_path):
    assert run("allowed_filetypes", ".md", scope_for(tmp_path, {"a.md": "x"})) == []


def test_files_are_list_or(tmp_path):
    s = scope_for(tmp_path, {"a.md": "x", "b.txt": "y"})
    assert run("allowed_filetypes", [".md", ".txt"], s) == []


def test_files_are_rejects_other(tmp_path):
    assert run("allowed_filetypes", [".md", ".txt"], scope_for(tmp_path, {"a.py": "x"}))


# --- frontmatter_has (REQUIRE: list = AND) -------------------------------

def test_frontmatter_all_present(tmp_path):
    s = scope_for(tmp_path, {"d.md": "---\ntitle: t\nsummary: s\n---\n# h\n"})
    assert run("required_frontmatter", ["title", "summary"], s) == []


def test_frontmatter_missing(tmp_path):
    s = scope_for(tmp_path, {"d.md": "---\ntitle: t\n---\n# h\n"})
    assert run("required_frontmatter", ["title", "summary"], s)


# --- forbidden_files (FORBID: none of these) -----------------------------

def test_forbidden_bare_name_anywhere(tmp_path):
    s = scope_for(tmp_path, {"nested/setup.py": "x"})
    assert run("forbidden_files", ["setup.py"], s)


def test_forbidden_glob(tmp_path):
    s = scope_for(tmp_path, {"app/settings.py": "x"})
    assert run("forbidden_files", ["**/settings.py"], s)


# --- required_files / folders --------------------------------------------

def test_required_files_missing(tmp_path):
    s = scope_for(tmp_path, {"a.py": "x"})
    assert run("required_files", "_todo.md", s)


def test_required_files_present(tmp_path):
    s = scope_for(tmp_path, {"_todo.md": "x"})
    assert run("required_files", "_todo.md", s) == []


def test_only_these_folders(tmp_path):
    s = scope_for(tmp_path, {"docs/a.md": "x", "src/b.py": "y", "weird/c": "z"}, locations=[""])
    violations = run("only_these_folders", ["docs", "src"], s)
    assert violations and "weird" in violations[0]


# --- must_not_exist ------------------------------------------------------

def test_must_not_exist_when_present(tmp_path):
    s = scope_for(tmp_path, {"legacy/a.py": "x"}, locations=["legacy"])
    assert run("must_not_exist", True, s)


def test_must_not_exist_when_absent(tmp_path):
    s = scope_for(tmp_path, {"src/a.py": "x"}, locations=["legacy"])
    assert run("must_not_exist", True, s) == []
