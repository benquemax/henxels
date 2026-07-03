"""The npm artifact, tested as users receive it: pack the tarball, install it, run it.

The cold-start test is the frontend-dev simulation — node + tar + coreutils on PATH and
nothing else; the launcher bootstraps uv, uv provisions Python, henxels runs pinned.
Network required, so everything here is `packaging`-marked: it gates CI and releases,
not everyday pushes.
"""

import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

pytestmark = [
    pytest.mark.packaging,
    pytest.mark.skipif(shutil.which("node") is None or shutil.which("npm") is None,
                       reason="node/npm not installed"),
    pytest.mark.skipif(sys.platform == "win32", reason="minimal-PATH symlinks are POSIX"),
]


def _install_packed_tarball(sandbox) -> Path:
    """npm pack (from a copy — prepack must not dirty the repo) + global install into
    the sandbox. Returns the installed `henxels` bin, exactly as a user would get it."""
    staging = sandbox.base / "pack"
    shutil.copytree(ROOT / "npm", staging / "npm")
    shutil.copy(ROOT / "README.md", staging / "README.md")  # what prepack copies in

    packed = sandbox.run(
        ["npm", "pack", "--json", "--pack-destination", str(sandbox.base)],
        cwd=staging / "npm", env_extra={"PATH": os.environ["PATH"]},
    )
    assert packed.returncode == 0, packed.stderr
    tarball = sandbox.base / json.loads(packed.stdout)[0]["filename"]

    names = tarfile.open(tarball).getnames()
    for rel in ("package/bin/henxels.js", "package/bin/bootstrap.cjs",
                "package/uv-manifest.json", "package/README.md"):
        assert rel in names, f"tarball is missing {rel}"

    prefix = sandbox.base / "npm-prefix"
    installed = sandbox.run(
        ["npm", "install", "-g", "--prefix", str(prefix), str(tarball)],
        cwd=sandbox.base, env_extra={"PATH": os.environ["PATH"]},
    )
    assert installed.returncode == 0, installed.stderr
    bin_path = prefix / "bin" / "henxels"
    assert bin_path.exists()
    return bin_path


def test_installed_package_resolves_its_own_files(sandbox):
    # No network, no engine: the override proves the installed bin, its relative
    # requires (package.json, bootstrap, manifest), and exit-code plumbing all work
    # in the post-install layout.
    bin_path = _install_packed_tarball(sandbox)
    result = sandbox.run(
        [shutil.which("node"), str(bin_path), "--version"],
        cwd=sandbox.base,
        env_extra={"HENXELS_SKIP_BOOTSTRAP": "1",
                   "HENXELS_ENGINE": f"{sys.executable} -m henxels", "PATH": ""},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "henxels v" in result.stdout


def test_cold_start_bootstraps_engine_and_runs_pinned_henxels(sandbox):
    bin_path = _install_packed_tarball(sandbox)

    # The documented minimal footprint: node + tar + POSIX coreutils (uv's entry shims
    # use realpath/dirname). Crucially absent: python, uv, uvx, henxels, gzip.
    bin_dir = sandbox.base / "bin"
    bin_dir.mkdir()
    for tool in ("node", "tar", "realpath", "dirname"):
        os.symlink(shutil.which(tool), bin_dir / tool)

    result = subprocess.run(
        ["node", str(bin_path), "catalogue"],
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
        ["node", str(bin_path), "catalogue"],
        capture_output=True, text=True, timeout=600,
        cwd=str(sandbox.base), env={**sandbox.env, "PATH": str(bin_dir)},
    )
    assert again.returncode == 0, again.stdout + again.stderr
    assert "fetching its engine" not in again.stderr
