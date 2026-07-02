"""E2E fixtures. Everything under tests/e2e/ is automatically marked `e2e`."""

import shutil

import pytest

from tests.e2e.harness import Sandbox


def pytest_collection_modifyitems(items):
    for item in items:
        if "/e2e/" in str(item.fspath).replace("\\", "/"):
            item.add_marker(pytest.mark.e2e)


@pytest.fixture
def sandbox(tmp_path):
    if shutil.which("git") is None:  # pragma: no cover
        pytest.skip("git not available")
    return Sandbox(tmp_path)
