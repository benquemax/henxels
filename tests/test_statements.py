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


def test_casing_allows_leading_underscore(tmp_path):
    # `_helpers.py` / `_private.py` are idiomatic Python, not violations
    assert run("filename_casing", "snake_case", scope_for(tmp_path, {"a/_helpers.py": "x"}, ["a"])) == []


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


def test_only_these_subfolders(tmp_path):
    s = scope_for(tmp_path, {"docs/a.md": "x", "src/b.py": "y", "weird/c": "z"}, locations=[""])
    violations = run("only_these_subfolders", ["docs", "src"], s)
    assert violations and "weird" in violations[0]


def test_required_subfolders(tmp_path):
    s = scope_for(tmp_path, {"pkg/__init__.py": "x"}, locations=["pkg"])
    assert run("required_subfolders", "sub", s)  # missing
    s2 = scope_for(tmp_path, {"pkg/sub/x.py": "x"}, locations=["pkg"])
    assert run("required_subfolders", "sub", s2) == []


def test_forbidden_subfolders(tmp_path):
    s = scope_for(tmp_path, {"pkg/bad/x.py": "x"}, locations=["pkg"])
    assert run("forbidden_subfolders", "bad", s)


def test_filename_matches_regex(tmp_path):
    s = scope_for(tmp_path, {"a/report_2024.md": "x"}, locations=["a"])
    assert run("filename_matches_regex", r"\d{4}", s) == []
    s2 = scope_for(tmp_path, {"a/report.md": "x"}, locations=["a"])
    assert run("filename_matches_regex", r"\d{4}", s2)


def test_markdown_lint_flags_issues(tmp_path):
    from henxels.statements.builtins import markdown_lint

    s = scope_for(tmp_path, {"docs/bad.md": "# Title \n\nno final newline"}, locations=["./docs"])
    assert markdown_lint(s)  # MD009 trailing space / MD047 missing final newline


def test_markdown_lint_clean(tmp_path):
    from henxels.statements.builtins import markdown_lint

    s = scope_for(tmp_path, {"docs/ok.md": "# Title\n\nHello world.\n"}, locations=["./docs"])
    assert markdown_lint(s) == []


def test_markdown_links_absolute(tmp_path):
    from henxels.statements.builtins.content import markdown_links_absolute

    s = scope_for(tmp_path, {"README.md": "See [contributing](CONTRIBUTING.md) and [site](https://x.com).\n"})
    out = markdown_links_absolute(s)
    assert out and "CONTRIBUTING.md" in out[0]
    assert not any("x.com" in v for v in out)  # absolute + external links are fine


def test_markdown_links_absolute_clean(tmp_path):
    from henxels.statements.builtins.content import markdown_links_absolute

    s = scope_for(tmp_path, {"README.md": "[a](https://github.com/x) and [b](#anchor).\n"})
    assert markdown_links_absolute(s) == []


def test_command_gates_registered():
    assert get_statement("run_before_commit").stage == "pre_commit"
    assert get_statement("run_before_push").stage == "pre_push"


def test_well_formed_statements_on_real_repo():
    # Dogfood: every built-in defined in this repo must have a help= and a test.
    from pathlib import Path

    from henxels.engine.discover import discover
    from henxels.statements.builtins import well_formed_statements

    root = Path(__file__).resolve().parent.parent
    scope = build_scope(["./*"], discover(root), root, {})
    assert well_formed_statements(scope) == []


# --- must_not_exist ------------------------------------------------------

def test_must_not_exist_when_present(tmp_path):
    s = scope_for(tmp_path, {"legacy/a.py": "x"}, locations=["legacy"])
    assert run("must_not_exist", True, s)


def test_must_not_exist_when_absent(tmp_path):
    s = scope_for(tmp_path, {"src/a.py": "x"}, locations=["legacy"])
    assert run("must_not_exist", True, s) == []
