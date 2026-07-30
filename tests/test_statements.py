"""Built-in statement vocabulary + scalar-or-list / OR / AND / none-of semantics."""

import pytest

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


# --- except: scope exclusions --------------------------------------------

def test_build_scope_excludes(tmp_path):
    files = {"a.md": "x", "raw/b.md": "y", "index.md": "z"}
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    s = build_scope(["./*"], list(files), tmp_path, {}, excludes=["./raw/*", "index.md"])
    assert s.files == ["a.md"]


def test_build_scope_no_excludes_keeps_all(tmp_path):
    files = {"a.md": "x", "raw/b.md": "y"}
    s = scope_for(tmp_path, files)  # excludes default to none
    assert set(s.files) == {"a.md", "raw/b.md"}


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


def test_frontmatter_null_value_counts_as_missing(tmp_path):
    # OKF conformance: `type` must be non-empty, so a bare `type:` doesn't declare it
    s = scope_for(tmp_path, {"d.md": "---\ntype:\ntitle: t\n---\n"})
    assert run("required_frontmatter", ["type", "title"], s)


def test_frontmatter_blank_string_counts_as_missing(tmp_path):
    s = scope_for(tmp_path, {"d.md": '---\ntype: ""\n---\n'})
    assert run("required_frontmatter", "type", s)


def test_frontmatter_empty_list_counts_as_missing(tmp_path):
    s = scope_for(tmp_path, {"d.md": "---\ntags: []\n---\n"})
    assert run("required_frontmatter", "tags", s)


def test_frontmatter_false_is_a_value_not_empty(tmp_path):
    s = scope_for(tmp_path, {"d.md": "---\ndraft: false\ncount: 0\n---\n"})
    assert run("required_frontmatter", ["draft", "count"], s) == []


# --- frontmatter_dates (ISO YYYY-MM-DD) ----------------------------------

def test_frontmatter_dates_quoted_valid(tmp_path):
    s = scope_for(tmp_path, {"d.md": '---\ncreated: "2026-06-28"\nupdated: "2026-06-28"\n---\n'})
    assert run("frontmatter_dates", ["created", "updated"], s) == []


def test_frontmatter_dates_accepts_yaml_date(tmp_path):
    s = scope_for(tmp_path, {"d.md": "---\ncreated: 2026-06-28\n---\n"})  # YAML parses to a date object
    assert run("frontmatter_dates", "created", s) == []


def test_frontmatter_dates_wrong_format(tmp_path):
    s = scope_for(tmp_path, {"d.md": "---\ncreated: 27/06/2026\n---\n"})
    assert run("frontmatter_dates", "created", s)


def test_frontmatter_dates_impossible_calendar(tmp_path):
    s = scope_for(tmp_path, {"d.md": '---\ncreated: "2026-13-40"\n---\n'})
    assert run("frontmatter_dates", "created", s)


def test_frontmatter_dates_absent_is_silent(tmp_path):
    s = scope_for(tmp_path, {"d.md": "---\ntitle: t\n---\n"})  # required_frontmatter owns presence
    assert run("frontmatter_dates", "created", s) == []


def test_frontmatter_dates_scalar_rejects_datetime(tmp_path):
    s = scope_for(tmp_path, {"d.md": "---\ncreated: 2026-05-22T10:00:00Z\n---\n"})
    assert run("frontmatter_dates", "created", s)


def test_frontmatter_dates_datetime_kind_accepts_unquoted(tmp_path):
    # OKF's `timestamp` is an ISO 8601 datetime; unquoted YAML parses it to a datetime object
    s = scope_for(tmp_path, {"d.md": "---\ntimestamp: 2026-05-22T10:00:00Z\n---\n"})
    assert run("frontmatter_dates", {"timestamp": "datetime"}, s) == []


def test_frontmatter_dates_datetime_kind_accepts_quoted(tmp_path):
    s = scope_for(tmp_path, {"d.md": '---\ntimestamp: "2026-05-22T10:00:00Z"\n---\n'})
    assert run("frontmatter_dates", {"timestamp": "datetime"}, s) == []


def test_frontmatter_dates_datetime_kind_accepts_date_precision(tmp_path):
    # a bare date is a valid ISO 8601 instant at day precision
    s = scope_for(tmp_path, {"d.md": "---\ntimestamp: 2026-05-22\n---\n"})
    assert run("frontmatter_dates", {"timestamp": "datetime"}, s) == []


def test_frontmatter_dates_datetime_kind_rejects_garbage(tmp_path):
    s = scope_for(tmp_path, {"d.md": "---\ntimestamp: yesterday at noon\n---\n"})
    assert run("frontmatter_dates", {"timestamp": "datetime"}, s)


def test_frontmatter_dates_dict_date_kind_stays_strict(tmp_path):
    s = scope_for(tmp_path, {"d.md": "---\ncreated: 2026-05-22T10:00:00Z\n---\n"})
    assert run("frontmatter_dates", {"created": "date"}, s)


def test_frontmatter_dates_unknown_kind_is_loud(tmp_path):
    s = scope_for(tmp_path, {"d.md": "---\ntimestamp: 2026-05-22\n---\n"})
    with pytest.raises(ValueError):
        run("frontmatter_dates", {"timestamp": "instant"}, s)


# --- frontmatter_values (scalar ∈ set; list ⊆ set) -----------------------

def test_frontmatter_values_scalar_ok(tmp_path):
    s = scope_for(tmp_path, {"d.md": "---\ntype: entity\n---\n"})
    assert run("frontmatter_values", {"type": ["entity", "concept"]}, s) == []


def test_frontmatter_values_scalar_bad(tmp_path):
    s = scope_for(tmp_path, {"d.md": "---\ntype: gizmo\n---\n"})
    assert run("frontmatter_values", {"type": ["entity", "concept"]}, s)


def test_frontmatter_values_list_subset_ok(tmp_path):
    s = scope_for(tmp_path, {"d.md": "---\ntags: [person, org]\n---\n"})
    assert run("frontmatter_values", {"tags": ["person", "org", "tool"]}, s) == []


def test_frontmatter_values_list_has_outsider(tmp_path):
    s = scope_for(tmp_path, {"d.md": "---\ntags: [person, alien]\n---\n"})
    assert run("frontmatter_values", {"tags": ["person", "org"]}, s)


# --- frontmatter_sha256_matches ------------------------------------------

def test_frontmatter_sha256_matches(tmp_path):
    import hashlib

    body = "The body text.\n"
    digest = hashlib.sha256(body.encode()).hexdigest()
    s = scope_for(tmp_path, {"raw/a.md": f"---\nsource_url: http://x\nsha256: {digest}\n---\n{body}"})
    assert run("frontmatter_sha256_matches", "sha256", s) == []


def test_frontmatter_sha256_mismatch(tmp_path):
    s = scope_for(tmp_path, {"raw/a.md": "---\nsha256: deadbeef\n---\nThe body text.\n"})
    assert run("frontmatter_sha256_matches", "sha256", s)


# --- no_frontmatter (e.g. OKF reserved files index.md / log.md) ------------

def test_no_frontmatter_flags_block(tmp_path):
    from henxels.statements.builtins.content import no_frontmatter

    s = scope_for(tmp_path, {"index.md": "---\ntitle: t\n---\n# Index\n"})
    assert no_frontmatter(s)


def test_no_frontmatter_flags_unparseable_block(tmp_path):
    from henxels.statements.builtins.content import no_frontmatter

    # the block itself is the violation, even when the YAML inside is garbage
    s = scope_for(tmp_path, {"index.md": "---\n: [broken\n---\n# Index\n"})
    assert no_frontmatter(s)


def test_no_frontmatter_clean_page_passes(tmp_path):
    from henxels.statements.builtins.content import no_frontmatter

    s = scope_for(tmp_path, {"index.md": "# Index\n\n* [a](a.md) - a concept\n"})
    assert no_frontmatter(s) == []


def test_no_frontmatter_unclosed_fence_is_not_a_block(tmp_path):
    from henxels.statements.builtins.content import no_frontmatter

    # an opening --- with no closing line is a horizontal rule, not frontmatter
    s = scope_for(tmp_path, {"index.md": "---\n# not frontmatter\n"})
    assert no_frontmatter(s) == []


def test_no_frontmatter_skips_non_markdown(tmp_path):
    from henxels.statements.builtins.content import no_frontmatter

    s = scope_for(tmp_path, {"data.yaml": "---\nkey: value\n---\n"})
    assert no_frontmatter(s) == []


# --- links ---------------------------------------------------------------

def test_links_resolve_ok(tmp_path):
    from henxels.statements.builtins.links import links_resolve

    s = scope_for(tmp_path, {"a.md": "see [b](b.md)\n", "b.md": "hi\n"})
    assert links_resolve(s) == []


def test_links_resolve_dead(tmp_path):
    from henxels.statements.builtins.links import links_resolve

    assert links_resolve(scope_for(tmp_path, {"a.md": "[gone](missing.md)\n"}))


def test_links_resolve_relative_subdir_and_anchor(tmp_path):
    from henxels.statements.builtins.links import links_resolve

    files = {"entities/a.md": "[x](../concepts/x.md) and [self](#top)\n", "concepts/x.md": "hi\n"}
    assert links_resolve(scope_for(tmp_path, files)) == []


def test_links_are_relative_flags_absolute(tmp_path):
    from henxels.statements.builtins.links import links_are_relative

    assert links_are_relative(scope_for(tmp_path, {"a.md": "[x](/abs/path.md)\n"}))


def test_links_are_relative_allows_external_and_relative(tmp_path):
    from henxels.statements.builtins.links import links_are_relative

    s = scope_for(tmp_path, {"a.md": "[x](b.md) and [y](https://x.com)\n"})
    assert links_are_relative(s) == []


def test_min_outbound_links(tmp_path):
    ok = scope_for(tmp_path, {"a.md": "[b](b.md) [c](c.md)\n"})  # one page, two outbound
    assert run("min_outbound_links", 2, ok) == []
    short = scope_for(tmp_path, {"a.md": "only [b](b.md)\n"})
    assert run("min_outbound_links", 2, short)


def test_referenced_in(tmp_path):
    files = {"index.md": "- [Tom](entities/tom.md)\n", "entities/tom.md": "x", "entities/ann.md": "y"}
    out = run("referenced_in", "index.md", scope_for(tmp_path, files))
    assert any("ann.md" in v for v in out)
    assert not any("tom.md" in v for v in out)


# --- rooted_links_resolve (root-absolute links, e.g. VitePress /a/b) ------

def test_rooted_links_resolve_ok(tmp_path):
    # /guide/intro -> guide/intro.md ; / -> index.md ; /guide/ -> guide/index.md ; #anchor dropped
    files = {
        "content/a.md": "[intro](/guide/intro#install) [home](/) [g](/guide/)\n",
        "content/guide/intro.md": "hi\n",
        "content/index.md": "home\n",
        "content/guide/index.md": "guide home\n",
    }
    assert run("rooted_links_resolve", "content", scope_for(tmp_path, files)) == []


def test_rooted_links_resolve_dead(tmp_path):
    out = run("rooted_links_resolve", "content", scope_for(tmp_path, {"content/a.md": "[gone](/guide/missing)\n"}))
    assert out and "/guide/missing" in out[0]


def test_rooted_links_resolve_ignores_relative_external_and_assets(tmp_path):
    # relative (links_resolve's job), external, in-page anchors, and asset files are skipped.
    # /slides.html is built output / a public asset (served at root), not a source page.
    files = {"content/a.md": "[rel](b.md) [ext](https://x.com) [img](/logo.png) [deck](/slides.html) [self](#top)\n"}
    assert run("rooted_links_resolve", "content", scope_for(tmp_path, files)) == []


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


def test_markdown_lint_passes_when_tool_missing(tmp_path, monkeypatch):
    from henxels.statements.builtins import content

    monkeypatch.setattr(content, "_pymarkdown_cmd", lambda: None)
    s = scope_for(tmp_path, {"docs/bad.md": "# Title \n\nno final newline"}, locations=["./docs"])
    assert content.markdown_lint(s) == []  # missing optional dep → pass, never block


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


def test_well_formed_statements_ignores_the_staged_subset():
    # `henxels check` and the pre-commit hook scope themselves to *staged* files, so
    # scope.all_files is a handful of paths, not the repo. "Is this statement covered
    # by a test?" is a repo-wide question: reading the staged subset made every
    # statement look untested and blocked commits that touched nothing related.
    from pathlib import Path

    from henxels.statements.builtins import well_formed_statements

    root = Path(__file__).resolve().parent.parent
    scope = build_scope(["./*"], ["README.md"], root, {})  # as if only README were staged
    assert well_formed_statements(scope) == []


# --- max_lines (per-file budget) -----------------------------------------

def test_max_lines(tmp_path):
    from henxels.statements.builtins.size import max_lines

    s = scope_for(tmp_path, {"a.md": "x\n" * 10})
    assert max_lines(5, "a.md", s)        # 10 > 5 → instruction
    assert max_lines(50, "a.md", s) is None


# --- no_secrets ----------------------------------------------------------

def test_no_secrets_flags_private_key(tmp_path):
    s = scope_for(tmp_path, {"a.md": "oops:\n-----BEGIN OPENSSH PRIVATE KEY-----\nabc\n"})
    assert run("no_secrets", True, s)


def test_no_secrets_flags_hardcoded(tmp_path):
    s = scope_for(tmp_path, {"a.md": 'password = "hunter2hunter2"\n'})
    assert run("no_secrets", True, s)


def test_no_secrets_clean(tmp_path):
    s = scope_for(tmp_path, {"a.md": "normal prose about tokens of wisdom and secret gardens\n"})
    assert run("no_secrets", True, s) == []


# --- must_not_exist ------------------------------------------------------

def test_must_not_exist_when_present(tmp_path):
    s = scope_for(tmp_path, {"legacy/a.py": "x"}, locations=["legacy"])
    assert run("must_not_exist", True, s)


def test_must_not_exist_when_absent(tmp_path):
    s = scope_for(tmp_path, {"src/a.py": "x"}, locations=["legacy"])
    assert run("must_not_exist", True, s) == []
