"""Catalogue + authoring scaffold + contribution guide."""

from henxels.catalogue import contribute_guide, create_statement_scaffold, render_catalogue


def test_catalogue_lists_builtins():
    out = render_catalogue()
    assert "Built-in" in out
    assert "casing" in out and "forbidden_files" in out
    assert "create-new-statement" in out
    assert "contribute" in out


def test_create_statement_scaffold_creates_and_appends(tmp_path):
    path, action = create_statement_scaffold("max_lines", tmp_path)
    assert action == "created"
    text = path.read_text()
    assert "from henxels import statement" in text
    assert '@statement("max_lines"' in text
    assert "def max_lines(" in text
    assert "contribute" in text

    path2, action2 = create_statement_scaffold("other-check", tmp_path)
    assert action2 == "updated"
    text2 = path2.read_text()
    assert text2.count("from henxels import statement") == 1  # header only once
    assert "def other_check(" in text2  # name sanitized to identifier


def test_contribute_guide_mentions_pr():
    out = contribute_guide()
    assert "ready-to-merge PR" in out
    assert "builtins.py" in out


def test_contribute_snippet_for_custom():
    from henxels import statement
    from henxels.catalogue import contribute_snippet

    @statement("cat_demo_custom")
    def cat_demo_custom(scope):
        return None

    source, test_stub = contribute_snippet("cat_demo_custom")
    assert "def cat_demo_custom" in source
    assert "def test_cat_demo_custom" in test_stub


def test_contribute_snippet_none_for_builtin():
    from henxels.catalogue import contribute_snippet

    assert contribute_snippet("filename_casing") is None  # built-ins aren't contributed
