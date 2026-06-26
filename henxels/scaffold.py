"""`henxels init` — detect the project, scaffold a starter contract, wire it up.

The scaffolded ``henxels.yaml`` is heavily commented on purpose: a small model should
be able to read it and know exactly what to change. Every starter ships sensible,
non-annoying defaults so henxels is useful the instant it lands.
"""

from __future__ import annotations

from pathlib import Path

from henxels.config.load import load_config
from henxels.digest import sync_file
from henxels.engine.gitinfo import is_git_repo
from henxels.hooks import install_hooks

SCHEMA_URL = (
    "https://raw.githubusercontent.com/benquemax/henxels/main/henxels/schema/henxels.schema.json"
)

_HEADER = f"""# henxels.yaml — your repo's contract. Read me top to bottom like a document.
# Change a rule here to change the rules; that's the only way to disobey responsibly.
# yaml-language-server: $schema={SCHEMA_URL}
henxels: 1
"""

_GUARDS = """
# Guards turn destructive reflexes into a conscious act.
# Override one time with `henxels bless <action>`; turn off for good by editing here.
guards:
  push: bless            # `git push` waits until you run `henxels bless push`
  delete:                # deleting files / removing many lines waits for a bless
    mode: bless
    line_threshold: 5    # net removed lines that trip the guard (diff-edit mistakes)
  stage: ask             # remind agents to let YOU stage and push
"""

_SIMILARITY = """
# Duplication awareness over committed files. Warnings only — never blocks.
similarity:
  warn_above: 0.85       # 0..1; higher = stricter about what counts as a near-copy
  exclude:               # files that are similar *by purpose* — skip them
    - "**/__init__.py"
"""


def _python_contract() -> str:
    return (
        _HEADER
        + _GUARDS
        + _SIMILARITY
        + """
# The one true home of a thing — forbid look-alikes that would duplicate it.
canonical:
  - role: "project config"
    file: pyproject.toml
    forbid_lookalikes: ["setup.py", "setup.cfg"]

# The tree mirrors your folders. Closest rule wins; rules cascade into subfolders.
tree:
  src:
    naming: snake_case
    forbid:
      - glob: "**/*_test.py"
        reason: "tests live in tests/, not beside the source"
        steer: "create the test under tests/ mirroring this path"
  tests:
    naming: snake_case
  docs:
    naming: kebab-case
"""
    )


def _node_contract() -> str:
    return (
        _HEADER
        + _GUARDS
        + _SIMILARITY
        + """
# The one true home of a thing — forbid look-alikes that would duplicate it.
canonical:
  - role: "package manifest"
    file: package.json
    forbid_lookalikes: []

# The tree mirrors your folders. Closest rule wins; rules cascade into subfolders.
tree:
  src:
    naming: kebab-case
  docs:
    naming: kebab-case
"""
    )


def _generic_contract() -> str:
    return (
        _HEADER
        + _GUARDS
        + _SIMILARITY
        + """
# The tree mirrors your folders. Closest rule wins; rules cascade into subfolders.
# Add folders and rules as you go — `henxels explain <path>` shows what applies.
tree:
  docs:
    naming: kebab-case
"""
    )


_CONTRACTS = {
    "python": _python_contract,
    "node": _node_contract,
    "generic": _generic_contract,
}


def detect_project(root: Path | str) -> str:
    """Sniff the ecosystem: 'python' | 'node' | 'generic'."""
    root = Path(root)
    if (root / "pyproject.toml").exists() or (root / "setup.py").exists() or (root / "setup.cfg").exists():
        return "python"
    if (root / "package.json").exists():
        return "node"
    return "generic"


def starter_contract(kind: str) -> str:
    return _CONTRACTS.get(kind, _generic_contract)()


def init(
    root: Path | str,
    install_git_hooks: bool = True,
    write_digest: bool = True,
    force: bool = False,
) -> dict:
    """Scaffold the contract, install hooks, write the digest. Returns a report dict."""
    root = Path(root)
    report: dict = {}

    cfg_path = root / "henxels.yaml"
    if cfg_path.exists() and not force:
        report["contract"] = ("exists", str(cfg_path))
        kind = detect_project(root)
    else:
        kind = detect_project(root)
        cfg_path.write_text(starter_contract(kind), encoding="utf-8")
        report["contract"] = ("created", kind)
    report["kind"] = kind

    if install_git_hooks and is_git_repo(root):
        report["hooks"] = install_hooks(root)
    else:
        report["hooks"] = None

    if write_digest:
        config = load_config(cfg_path)
        report["digest"] = sync_file(root / "AGENTS.md", config)
    else:
        report["digest"] = None

    return report
