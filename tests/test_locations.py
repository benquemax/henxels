"""`in:` path parsing — explicit recursion via the trailing asterisk."""

from henxels.locations import parse


def test_folder_non_recursive():
    loc = parse("./docs")
    assert loc.kind == "folder" and loc.base == "docs" and not loc.recursive
    assert loc.matches("docs/intro.md")          # direct file
    assert not loc.matches("docs/sub/deep.md")   # subfolder excluded


def test_folder_recursive():
    loc = parse("./docs/*")
    assert loc.recursive
    assert loc.matches("docs/intro.md")
    assert loc.matches("docs/sub/deep.md")
    assert not loc.matches("src/x.py")


def test_double_star_recursive_alias():
    assert parse("./docs/**").recursive is True


def test_root_levels():
    root = parse("./")
    assert root.matches("README.md")
    assert not root.matches("docs/x.md")
    whole = parse("./*")
    assert whole.matches("README.md") and whole.matches("docs/sub/x.md")


def test_specific_file():
    loc = parse("./docs/intro.md")
    assert loc.kind == "file"
    assert loc.matches("docs/intro.md")
    assert not loc.matches("docs/other.md")


def test_glob():
    loc = parse("./docs/*.md")
    assert loc.kind == "glob" and loc.base == "docs"
    assert loc.matches("docs/intro.md")
    assert not loc.matches("docs/intro.txt")


def test_leading_dot_optional():
    assert parse("docs").matches("docs/x.md")  # accepted without ./


def test_base_for_existence_statements():
    assert parse("./docs").base == "docs"
    assert parse("./docs/*").base == "docs"
    assert parse("./").base == ""
    assert parse("./*").base == ""


# A wiki whose root IS the repo root: `okf-llm-wiki --wiki-dir .` substitutes
# wiki="." into `./$wiki/...`, producing `././*` and `./.`. parse() stripped the
# leading "./" exactly once, leaving a literal folder named "." that no
# repo-relative path can ever be under — so every rule scoped that way matched
# nothing and the contract was silently inert.


def test_redundant_current_dir_segment_is_the_repo_root():
    loc = parse("././*")
    assert loc.kind == "folder" and loc.base == "" and loc.recursive
    assert loc.matches("brainpick.md")
    assert loc.matches("journals/2026-09-18.md")


def test_dot_dot_slash_is_the_repo_root_level():
    loc = parse("./.")
    assert loc.kind == "folder" and loc.base == ""
    assert loc.matches("index.md")
    assert not loc.matches("journals/x.md")   # this level only


def test_redundant_dot_in_a_glob():
    loc = parse("././**/index.md")
    assert loc.matches("index.md")
    assert loc.matches("journals/index.md")


def test_redundant_dot_before_a_named_folder():
    loc = parse("././docs")
    assert loc.base == "docs"
    assert loc.matches("docs/x.md")


def test_governs_follows_the_same_normalization():
    assert parse("././*").governs("skills/a.md")
