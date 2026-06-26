"""Glob semantics — the matcher that backs forbid/exclude henxels."""

import pytest

from henxels.util.glob import glob_match


@pytest.mark.parametrize(
    "pattern,path,expected",
    [
        # ** spans directories AND zero directories
        ("**/*_test.py", "foo_test.py", True),
        ("**/*_test.py", "api/foo_test.py", True),
        ("**/*_test.py", "a/b/c/foo_test.py", True),
        ("**/*_test.py", "foo.py", False),
        # * stays within a segment
        ("*.py", "foo.py", True),
        ("*.py", "sub/foo.py", False),
        ("src/*.py", "src/foo.py", True),
        ("src/*.py", "src/sub/foo.py", False),
        # trailing /** captures the subtree
        ("src/**", "src/a.py", True),
        ("src/**", "src/a/b.py", True),
        ("src/**", "lib/a.py", False),
        # multi-dot purpose patterns (e.g. similarity excludes)
        ("**/*.test.*", "a/b/foo.test.js", True),
        ("**/*.test.*", "foo.test.tsx", True),
        ("**/*.test.*", "foo.py", False),
        # ? matches exactly one non-slash char
        ("v?.md", "v1.md", True),
        ("v?.md", "v12.md", False),
        # literal dots are not wildcards
        ("readme.md", "readmeXmd", False),
    ],
)
def test_glob_match(pattern, path, expected):
    assert glob_match(pattern, path) is expected


def test_backslashes_normalized():
    assert glob_match("src/**", "src\\a\\b.py") is True
