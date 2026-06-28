"""The v2 contract: a list of henxels (tests) plus settings (behaviours).

A henxel is one bullet on the whiteboard: a sentence, an optional ``in:`` scope, an
optional ``level:``, and a set of statements (``name: params``) that must all pass.
The sentence is the failure message. Logic lives inside the statement functions, not
in the YAML — so the surface stays a dumb, readable list.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Keys on a henxel item that are NOT statements.
HEADLINE_KEYS = ("henxel", "rule", "must", "description")
# Free-text reasoning/background for a henxel — not a test; it just rides into the
# AGENTS.md digest (and `explain`) so agents read the *purpose* of the structure.
CONTEXT_KEYS = ("why", "context", "comment")
RESERVED = set(HEADLINE_KEYS) | set(CONTEXT_KEYS) | {"in", "level", "except"}


DEFAULT_FILENAMES = ("henxels.yaml", ".henxels.yaml", "henxels.yml", ".henxels.yml")


class ContractError(Exception):
    """The contract is missing or malformed."""


def find_contract(start: Path | str = ".") -> Path | None:
    start = Path(start)
    for name in DEFAULT_FILENAMES:
        candidate = start / name
        if candidate.is_file():
            return candidate
    return None


@dataclass
class Henxel:
    text: str  # the sentence (and the failure message)
    locations: list[str] = field(default_factory=lambda: ["./*"])  # raw `in:` specs
    excludes: list[str] = field(default_factory=list)  # raw `except:` specs carved out of scope
    level: str = "block"  # block | warn
    why: str = ""  # free-text reasoning/background (surfaced in the digest + explain)
    statements: dict = field(default_factory=dict)  # {name: params}, excludes reserved keys


@dataclass
class Contract:
    settings: dict = field(default_factory=dict)
    henxels: list[Henxel] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    path: Path | None = None
    raw: dict = field(default_factory=dict)


def load_contract(path: Path | str) -> Contract:
    path = Path(path)
    if not path.is_file():
        raise ContractError(f"Contract file not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ContractError(f"Could not parse {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ContractError(f"Contract at {path} must be a mapping")

    henxels = [_to_henxel(item) for item in _as_list(raw.get("henxels")) if isinstance(item, dict)]
    return Contract(
        settings=raw.get("settings") if isinstance(raw.get("settings"), dict) else {},
        henxels=henxels,
        imports=_as_list(raw.get("imports")),
        path=path,
        raw=raw,
    )


def _to_henxel(item: dict) -> Henxel:
    text = next((str(item[k]) for k in HEADLINE_KEYS if k in item), "(unnamed henxel)")
    why = next((str(item[k]) for k in CONTEXT_KEYS if k in item), "")
    locations = _norm_locations(item.get("in"))
    excludes = _norm_excludes(item.get("except"))
    level = "warn" if str(item.get("level", "")).lower() == "warn" else "block"
    statements = {k: v for k, v in item.items() if k not in RESERVED}
    return Henxel(text=text, locations=locations, excludes=excludes, level=level, why=why, statements=statements)


def _norm_locations(value) -> list[str]:
    if value is None:
        return ["./*"]
    out = [str(v).strip() for v in (value if isinstance(value, list) else [value])]
    return out or ["./*"]


def _norm_excludes(value) -> list[str]:
    """`except:` carves files out of scope. Absent = exclude nothing (NOT the whole repo)."""
    if value is None:
        return []
    return [str(v).strip() for v in (value if isinstance(value, list) else [value])]


# Drop a file at one of these (relative to the repo root) and henxels auto-loads it —
# no `imports:` needed. A whole `.henxels/` folder of check modules also works.
LOCAL_CHECK_FILES = ("henxels_checks.py",)
LOCAL_CHECK_DIR = ".henxels"


def apply_imports(contract: Contract, root: Path | str | None = None) -> list[str]:
    """Load custom-statement modules: explicit ``imports:`` + auto-discovered local
    check files. Returns the refs that failed to import."""
    base = Path(root) if root else (contract.path.parent if contract.path else Path.cwd())
    failed: list[str] = []

    refs = list(contract.imports) + _local_check_refs(base)
    for ref in refs:
        try:
            _import_ref(ref, base=base)
        except Exception:  # noqa: BLE001 - report, don't crash the run
            failed.append(ref)
    return failed


def _local_check_refs(base: Path) -> list[str]:
    refs: list[str] = []
    for name in LOCAL_CHECK_FILES:
        if (base / name).is_file():
            refs.append(name)
    check_dir = base / LOCAL_CHECK_DIR
    if check_dir.is_dir():
        refs.extend(
            str((check_dir / f.name).relative_to(base))
            for f in sorted(check_dir.glob("*.py"))
            if not f.name.startswith("_")
        )
    return refs


def _import_ref(ref: str, base: Path) -> None:
    if ref.endswith(".py") or "/" in ref:
        file = (base / ref).resolve()
        spec = importlib.util.spec_from_file_location(file.stem, file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    else:
        importlib.import_module(ref)


def _as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]
