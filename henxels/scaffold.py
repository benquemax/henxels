"""`henxels init` — detect the project, scaffold a v2 contract, wire it up.

The starter is a heavily-commented whiteboard list so a small model can read it and
know exactly what to change. Use-case templates (``--template okf-llm-wiki``) ride on
top: they append their henxels to the detected starter and, on an empty repo, seed just
enough content that the contract holds from the first minute (green at birth).
"""

from __future__ import annotations

import datetime
import os
from pathlib import Path
from string import Template

from henxels.contract import load_contract
from henxels.digest import sync_file
from henxels.engine.discover import DEFAULT_EXCLUDES
from henxels.engine.gitinfo import is_git_repo, shadowing_hooks_path
from henxels.hooks import install_hooks
from henxels.schema import schema_text


class ScaffoldError(Exception):
    """init could not proceed; the message is an instruction, not a complaint."""

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

# --- use-case templates ----------------------------------------------------

TEMPLATES = ("okf-llm-wiki",)
DEFAULT_WIKI_DIR = "wiki"
_MIN_WIKI_MD = 3  # markdown files that make a folder look like an existing wiki

# Wiki-tuned settings: knowledge is easy to lose and easy to scatter.
_OKF_SETTINGS = """
# Behaviours (not tests): protections + tuning knobs.
settings:
  ask_me_before_staging: true     # don't `git add` for me — ask instead
  confirm_before_push: true       # block `git push` until `henxels bless push`
  confirm_before_deleting:        # knowledge doesn't vanish to a diff slip
    over_lines: 10
  warn_about_similar_files:       # one concept, ONE document — update it,
    above: 0.82                   # don't clone a near-duplicate
    ignore: ["**/__init__.py", "**/index.md", "**/log.md"]
"""

# The OKF wiki henxels, appended to the detected starter's `henxels:` list.
_OKF_WIKI = Template("""
  # --- the OKF wiki (okf-llm-wiki template) --------------------------------
  # The bundle in $wiki/ follows the Open Knowledge Format:
  # https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
  - henxel: "Every concept doc is kebab-case markdown with OKF frontmatter (type is the one MUST)"
    in: ./$wiki/*
    except: ["**/index.md", "**/log.md", "$wiki/references/*"]
    allowed_filetypes: .md
    filename_casing: kebab-case
    required_frontmatter: [type, title, description]
    # Pin your concept-type taxonomy once it settles (OKF: producers pick their own):
    # frontmatter_values:
    #   type: [BigQuery Table, API Endpoint, Metric, Playbook]

  - henxel: "timestamp is a real ISO 8601 datetime and is bumped when a doc changes"
    in: ./$wiki/*
    except: ["**/index.md", "**/log.md", "$wiki/references/*"]
    frontmatter_dates: { timestamp: datetime }
    bump_updated_on_change: timestamp

  - henxel: "Every link lands — bundle-absolute (/a/b.md) and relative alike"
    in: ./$wiki/*
    rooted_links_resolve: ./$wiki
    links_resolve: true

  - henxel: "A concept is a node in the knowledge graph, not an orphan"
    in: ./$wiki/*
    except: ["**/index.md", "**/log.md", "$wiki/references/*"]
    min_outbound_links: 1

  - henxel: "OKF reserved files stay frontmatter-free (the bundle root may declare okf_version)"
    in: ["./$wiki/**/index.md", "./$wiki/**/log.md"]
    except: ./$wiki/index.md
    no_frontmatter: true

  - henxel: "Update logs are date-sectioned, newest first"
    in: ./$wiki/**/log.md
    log_headings_are_dates: true    # custom check, lives in henxels_checks.py

  - henxel: "The bundle root has an index and every top-level concept is listed in it"
    in: ./$wiki
    except: "**/log.md"
    required_files: index.md
    referenced_in: $wiki/index.md
""")

# Ships with the template; identical to the check shown in docs/enforcing-okf.md.
_OKF_CHECKS_PY = '''"""Custom checks for the OKF wiki (scaffolded by `henxels init --template okf-llm-wiki`)."""

import datetime
import re

from henxels import statement

_SECTION = re.compile(r"^##\\s+(.+?)\\s*$")


@statement("log_headings_are_dates", help="log.md sections are '## YYYY-MM-DD' headings, newest first")
def log_headings_are_dates(file, scope):
    dates, problems = [], []
    for line in (scope.read_text(file) or "").splitlines():
        m = _SECTION.match(line)
        if not m:
            continue
        try:
            dates.append(datetime.date.fromisoformat(m.group(1)))
        except ValueError:
            problems.append(f"section '{m.group(1)}' — head log sections with an ISO date: ## YYYY-MM-DD")
    if dates != sorted(dates, reverse=True):
        problems.append("order the date sections newest first")
    return problems
'''

_SEED_INDEX = """---
okf_version: "0.1"
---

# Knowledge bundle

## Concepts

* [Wiki conventions](wiki-conventions.md) - how concepts in this wiki are written
"""

_SEED_CONCEPT = """---
type: Playbook
title: Wiki conventions
description: How concepts in this wiki are written and linked.
timestamp: {today}
---

# Wiki conventions

One concept, one markdown file, with OKF frontmatter — `type` is required; `title`,
`description`, and `timestamp` keep it findable. Link concepts to each other
bundle-absolutely (from the wiki root, like [the index](/index.md)) so links survive
refactors, and list every new top-level concept in the index.
"""

_SEED_LOG = """# Bundle update log

## {today}

* **Creation**: Wiki initialized with the okf-llm-wiki henxels template.
"""


def wiki_candidates(root: Path | str) -> list[tuple[str, int]]:
    """Top-level folders dense enough in markdown to look like an existing wiki."""
    out = []
    for entry in os.scandir(Path(root)):
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in DEFAULT_EXCLUDES:
            continue
        count = sum(1 for _ in Path(entry.path).rglob("*.md"))
        if count >= _MIN_WIKI_MD:
            out.append((entry.name, count))
    return sorted(out, key=lambda item: (-item[1], item[0]))


def resolve_wiki_dir(root: Path | str, wiki_dir: str | None = None, ask=None) -> str:
    """Which folder the wiki template governs. Explicit flag > existing default >
    scaffold the default — and when the default is absent but markdown-dense folders
    exist, require explicitness rather than guess (``ask`` may settle it on a TTY)."""
    root = Path(root)
    if wiki_dir:
        return str(wiki_dir).strip().removeprefix("./").strip("/")
    if (root / DEFAULT_WIKI_DIR).is_dir():
        return DEFAULT_WIKI_DIR
    candidates = wiki_candidates(root)
    if not candidates:
        return DEFAULT_WIKI_DIR
    if ask is not None:
        choice = ask(candidates)
        if choice:
            return str(choice).strip().removeprefix("./").strip("/")
    raise ScaffoldError(_ambiguous_wiki_message(candidates))


def _ambiguous_wiki_message(candidates: list[tuple[str, int]]) -> str:
    from henxels.invocation import henxels_cmd

    hx = henxels_cmd()
    listing = "\n".join(f"  {name}/ ({count} markdown files)" for name, count in candidates)
    first = candidates[0][0]
    return (
        "Found existing markdown that might be your wiki:\n"
        f"{listing}\n"
        "Say which folder the contract should govern:\n\n"
        f"    {hx} init --template okf-llm-wiki --wiki-dir {first}\n\n"
        "or start a fresh wiki alongside it:\n\n"
        f"    {hx} init --template okf-llm-wiki --wiki-dir {DEFAULT_WIKI_DIR}"
    )


def _okf_fragment(wiki: str, warn: bool) -> str:
    """The wiki henxels; in migrate mode every rule starts at ``level: warn`` so an
    existing wiki gets a migration plan, not blocked commits."""
    fragment = _OKF_WIKI.substitute(wiki=wiki)
    if not warn:
        return fragment
    out = []
    for line in fragment.splitlines(keepends=True):
        out.append(line)
        if line.lstrip().startswith("- henxel:"):
            out.append("    level: warn\n")
    return "".join(out)


def _okf_seeds(wiki: str) -> dict[str, str]:
    today = datetime.date.today().isoformat()
    return {
        f"{wiki}/index.md": _SEED_INDEX,
        f"{wiki}/wiki-conventions.md": _SEED_CONCEPT.format(today=today),
        f"{wiki}/log.md": _SEED_LOG.format(today=today),
    }


def detect_project(root: Path | str) -> str:
    root = Path(root)
    if (root / "pyproject.toml").exists() or (root / "setup.py").exists() or (root / "setup.cfg").exists():
        return "python"
    if (root / "package.json").exists():
        return "node"
    return "generic"


def starter_contract(kind: str) -> str:
    return _HEADER + _SETTINGS + _CONTRACTS.get(kind, _GENERIC)


def init(
    root: Path | str,
    install_git_hooks: bool = True,
    adopt_hooks: bool = False,
    write_digest: bool = True,
    force: bool = False,
    template: str | None = None,
    wiki_dir: str | None = None,
    dry_run: bool = False,
    ask=None,
) -> dict:
    root = Path(root)
    report: dict = {}

    if template is not None and template not in TEMPLATES:
        raise ScaffoldError(f"unknown template '{template}' — available: {', '.join(TEMPLATES)}")

    wiki = mode = None
    if template:
        wiki = resolve_wiki_dir(root, wiki_dir, ask=ask)
        occupied = (root / wiki).is_dir() and any(p.is_file() for p in (root / wiki).rglob("*"))
        mode = "governing" if occupied else "scaffolded"
        report["template"] = template
        report["wiki"] = (mode, wiki)

    cfg_path = root / "henxels.yaml"
    kind = detect_project(root)
    report["kind"] = kind

    if dry_run:
        report["dry_run"] = True
        report["contract"] = ("exists", str(cfg_path)) if cfg_path.exists() and not force else ("planned", kind)
        return report

    fragment = _okf_fragment(wiki, warn=(mode == "governing")) if template else ""
    if cfg_path.exists() and not force:
        report["contract"] = ("exists", str(cfg_path))
        if template:
            report["fragment"] = fragment  # paste-able: never edit an existing contract
    else:
        body = _HEADER + (_OKF_SETTINGS if template else _SETTINGS) + _CONTRACTS.get(kind, _GENERIC) + fragment
        cfg_path.write_text(body, encoding="utf-8")
        report["contract"] = ("created", kind)

    if template:
        checks_path = root / "henxels_checks.py"
        if checks_path.exists():
            report["checks_file"] = ("exists", "henxels_checks.py")
        else:
            checks_path.write_text(_OKF_CHECKS_PY, encoding="utf-8")
            report["checks_file"] = ("created", "henxels_checks.py")

    if template and mode == "scaffolded" and report["contract"][0] == "created":
        written = []
        for rel, content in _okf_seeds(wiki).items():
            path = root / rel
            if path.exists():
                continue  # additive only — never overwrite wiki content
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            written.append(rel)
        report["seeds"] = written

    # Local schema copy → editor autocomplete works offline / in private repos.
    write_local_schema(root)
    report["schema"] = LOCAL_SCHEMA_PATH

    report["hooks"] = (
        install_hooks(root, adopt=adopt_hooks)
        if (install_git_hooks and is_git_repo(root))
        else None
    )
    # If core.hooksPath (husky, etc.) shadows .git/hooks, the hooks we wrote there won't
    # fire — record it so init warns instead of a silent no-op.
    report["hooks_shadowed"] = shadowing_hooks_path(root) if report["hooks"] else None

    if write_digest:
        contract = load_contract(cfg_path)
        report["digest"] = sync_file(root / "AGENTS.md", contract)
    else:
        report["digest"] = None

    return report
