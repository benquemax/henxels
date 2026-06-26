"""`henxels init` — detect the project, scaffold a v2 contract, wire it up.

The starter is a heavily-commented whiteboard list so a small model can read it and
know exactly what to change.
"""

from __future__ import annotations

from pathlib import Path

from henxels.contract import load_contract
from henxels.digest import sync_file
from henxels.engine.gitinfo import is_git_repo
from henxels.hooks import install_hooks
from henxels.schema import schema_text

# A local schema copy (written by init) gives editors autocomplete offline and in
# private repos — no fetch from a maybe-private GitHub URL required.
LOCAL_SCHEMA_PATH = ".henxels/henxels.schema.json"
LOCAL_SCHEMA_REL = f"./{LOCAL_SCHEMA_PATH}"

_HEADER = f"""# henxels.yaml — a whiteboard list of rules. Each bullet is one henxel.
# Change a rule here to change the rules; that's the only way to disobey responsibly.
# yaml-language-server: $schema={LOCAL_SCHEMA_REL}
"""


def write_local_schema(root: Path | str) -> Path:
    """Write the bundled JSON Schema into the repo so editors can resolve it locally."""
    path = Path(root) / LOCAL_SCHEMA_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(schema_text(), encoding="utf-8")
    return path

_SETTINGS = """
# Behaviours (not tests): protections + tuning knobs.
settings:
  ask_me_before_staging: true     # don't `git add` for me — ask instead
  confirm_before_push: true       # block `git push` until `henxels bless push`
  confirm_before_deleting:        # losing files / many lines must be deliberate
    over_lines: 5
  warn_about_similar_files:       # nudge when a new file looks like a copy
    above: 0.85
    ignore: ["**/__init__.py"]
"""

# Note the `in:` syntax: ./src = files directly in src/; ./src/* = src/ recursively;
# ./ = repo root; ./* = whole repo (the default when `in:` is omitted).
_PYTHON = """
# Rules. Browse `henxels catalogue` for the statements you can use; write your own
# with `henxels create-new-statement`.
henxels:
  - henxel: "Source files live in src/ and are snake_case"
    in: ./src/*
    filename_casing: snake_case
  - henxel: "Tests are snake_case and live in tests/"
    in: ./tests/*
    filename_casing: snake_case
  - henxel: "Docs are kebab-case markdown"
    in: ./docs
    allowed_filetypes: .md
    filename_casing: kebab-case
  - henxel: "Project config lives only in pyproject.toml"
    forbidden_files: [setup.py, setup.cfg]
  - henxel: "The test suite passes before every commit"
    run_before_commit: "uv run pytest -q"
"""

_NODE = """
henxels:
  - henxel: "Source files in src/ are kebab-case"
    in: ./src/*
    filename_casing: kebab-case
  - henxel: "Docs are kebab-case markdown"
    in: ./docs
    allowed_filetypes: .md
    filename_casing: kebab-case
"""

_GENERIC = """
# Add rules as you go. `henxels explain <path>` shows what applies to a path.
henxels:
  - henxel: "Docs are kebab-case markdown"
    in: ./docs
    allowed_filetypes: .md
    filename_casing: kebab-case
"""

_CONTRACTS = {"python": _PYTHON, "node": _NODE, "generic": _GENERIC}


def detect_project(root: Path | str) -> str:
    root = Path(root)
    if (root / "pyproject.toml").exists() or (root / "setup.py").exists() or (root / "setup.cfg").exists():
        return "python"
    if (root / "package.json").exists():
        return "node"
    return "generic"


def starter_contract(kind: str) -> str:
    return _HEADER + _SETTINGS + _CONTRACTS.get(kind, _GENERIC)


def init(root: Path | str, install_git_hooks: bool = True, write_digest: bool = True, force: bool = False) -> dict:
    root = Path(root)
    report: dict = {}

    cfg_path = root / "henxels.yaml"
    kind = detect_project(root)
    if cfg_path.exists() and not force:
        report["contract"] = ("exists", str(cfg_path))
    else:
        cfg_path.write_text(starter_contract(kind), encoding="utf-8")
        report["contract"] = ("created", kind)
    report["kind"] = kind

    # Local schema copy → editor autocomplete works offline / in private repos.
    write_local_schema(root)
    report["schema"] = LOCAL_SCHEMA_PATH

    report["hooks"] = install_hooks(root) if (install_git_hooks and is_git_repo(root)) else None

    if write_digest:
        contract = load_contract(cfg_path)
        report["digest"] = sync_file(root / "AGENTS.md", contract)
    else:
        report["digest"] = None

    return report
