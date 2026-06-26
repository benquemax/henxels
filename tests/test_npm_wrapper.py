"""The npm launcher must be present and well-formed (node optional)."""

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NPM = ROOT / "npm"


def test_package_json_valid():
    data = json.loads((NPM / "package.json").read_text(encoding="utf-8"))
    assert data["name"] == "henxels"
    assert data["bin"]["henxels"] == "bin/henxels.js"


def test_launcher_exists():
    launcher = NPM / "bin" / "henxels.js"
    assert launcher.is_file()
    assert launcher.read_text(encoding="utf-8").startswith("#!/usr/bin/env node")


def test_launcher_runs_if_node_available():
    node = shutil.which("node")
    if node is None:
        return  # node not installed in this environment — skip silently
    # The launcher should reach the Python engine and print help (exit 0).
    result = subprocess.run(
        [node, str(NPM / "bin" / "henxels.js")],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0
    assert "henxels" in (result.stdout + result.stderr).lower()
