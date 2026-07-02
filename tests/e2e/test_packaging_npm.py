"""The frontend-dev cold start, for real: node + the npm launcher and nothing else.

Network required (downloads uv from GitHub, Python + henxels via uv), so this is
`packaging`-marked: it gates releases and CI packaging jobs, not everyday pushes.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

pytestmark = [
    pytest.mark.packaging,
    pytest.mark.skipif(shutil.which("node") is None, reason="node not installed"),
    pytest.mark.skipif(sys.platform == "win32", reason="minimal-PATH symlinks are POSIX"),
]


def test_cold_start_bootstraps_engine_and_runs_pinned_henxels(sandbox):
    # The documented minimal footprint: node + tar + POSIX coreutils (uv's entry shims
    # use realpath/dirname). Crucially absent: python, uv, uvx, henxels, gzip.
    bin_dir = sandbox.base / "bin"
    bin_dir.mkdir()
    for tool in ("node", "tar", "realpath", "dirname"):
        os.symlink(shutil.which(tool), bin_dir / tool)

    result = subprocess.run(
        ["node", str(ROOT / "npm" / "bin" / "henxels.js"), "catalogue"],
        capture_output=True, text=True, timeout=600,
        cwd=str(sandbox.base), env={**sandbox.env, "PATH": str(bin_dir)},
    )
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "first run — fetching its engine" in result.stderr  # the bootstrap actually ran
    assert "filename_casing" in result.stdout  # a real engine answered, not a stub

    # The zero-Python claim, verified: uv provisioned a managed interpreter inside the
    # sandbox — it did not quietly borrow one from the host.
    managed = list((sandbox.base / "home").glob(".local/share/uv/python/*"))
    assert managed, "expected a uv-managed Python under the sandbox home"

    # Second run must reuse the cached engine: no bootstrap line this time.
    again = subprocess.run(
        ["node", str(ROOT / "npm" / "bin" / "henxels.js"), "catalogue"],
        capture_output=True, text=True, timeout=600,
        cwd=str(sandbox.base), env={**sandbox.env, "PATH": str(bin_dir)},
    )
    assert again.returncode == 0, again.stdout + again.stderr
    assert "fetching its engine" not in again.stderr
