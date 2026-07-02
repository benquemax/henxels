"""The npm launcher: version-pinned engine chain, bootstrap manifest, and fallbacks."""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
NPM = ROOT / "npm"
NODE = shutil.which("node")

needs_node = pytest.mark.skipif(NODE is None, reason="node not installed")
posix_only = pytest.mark.skipif(sys.platform == "win32", reason="fake-bin scripts are POSIX")


def _package():
    return json.loads((NPM / "package.json").read_text(encoding="utf-8"))


def _launch(*args, env=None, path=""):
    base = {
        "PATH": path,
        "HENXELS_SKIP_BOOTSTRAP": "1",  # unit tier never touches the network
        "HOME": os.environ.get("HOME", "/tmp"),
    }
    return subprocess.run(
        [NODE, str(NPM / "bin" / "henxels.js"), *args],
        capture_output=True, text=True, cwd=ROOT, env={**base, **(env or {})}, timeout=60,
    )


def test_package_json_valid():
    data = _package()
    assert data["name"] == "henxels"
    assert data["bin"]["henxels"] == "bin/henxels.js"
    assert "bin/bootstrap.cjs" in data["files"]
    assert "uv-manifest.json" in data["files"]


def test_uv_manifest_is_pinned_and_complete():
    manifest = json.loads((NPM / "uv-manifest.json").read_text(encoding="utf-8"))
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])
    expected = {
        "linux-x64-gnu", "linux-arm64-gnu", "linux-x64-musl", "linux-arm64-musl",
        "darwin-x64", "darwin-arm64", "win32-x64", "win32-arm64", "win32-ia32",
    }
    assert set(manifest["assets"]) == expected
    for entry in manifest["assets"].values():
        assert entry["asset"].startswith("uv-")
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])


@needs_node
def test_engine_override_wins():
    result = _launch("check", env={"HENXELS_ENGINE": f"{sys.executable} -m henxels --version"})
    # override command runs with our args appended; --version makes argparse exit 0 first
    assert result.returncode == 0
    assert "henxels v" in result.stdout


@needs_node
@posix_only
def test_uvx_is_tried_first_with_the_pinned_version(tmp_path):
    capture = tmp_path / "argv.txt"
    fake = tmp_path / "uvx"
    fake.write_text(f"#!/bin/sh\necho \"$@\" > {capture}\nexit 0\n", encoding="utf-8")
    fake.chmod(0o755)
    result = _launch("init", "--dry-run", path=str(tmp_path))
    assert result.returncode == 0
    assert capture.read_text(encoding="utf-8").strip() == f"henxels@{_package()['version']} init --dry-run"


@needs_node
@posix_only
def test_real_engine_failure_is_not_masked(tmp_path):
    fake = tmp_path / "uvx"
    fake.write_text("#!/bin/sh\necho engine exploded >&2\nexit 3\n", encoding="utf-8")
    fake.chmod(0o755)
    result = _launch("check", path=str(tmp_path))
    assert result.returncode == 3  # an engine that RAN and failed propagates — no cascading
    assert "engine exploded" in result.stderr


@needs_node
def test_no_engine_is_an_instruction(tmp_path):
    result = _launch("check", path=str(tmp_path))  # empty PATH, bootstrap skipped
    assert result.returncode == 127
    out = result.stderr
    assert "uv" in out and "pip install henxels" in out


def test_launcher_and_bootstrap_are_wellformed():
    launcher = (NPM / "bin" / "henxels.js").read_text(encoding="utf-8")
    assert launcher.startswith("#!/usr/bin/env node")
    assert "uv-manifest.json" in (NPM / "bin" / "bootstrap.cjs").read_text(encoding="utf-8")
