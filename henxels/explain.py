"""`henxels explain <path>` — which henxels govern a location, in plain words.

Before creating or moving a file, an agent asks what applies here. We list every
henxel whose ``in:`` covers the path and the statements it must satisfy.
"""

from __future__ import annotations

from henxels.contract import Contract
from henxels.locations import parse_all


def explain_path(contract: Contract, rel_path: str) -> str:
    path = str(rel_path).replace("\\", "/").strip("/")
    lines = [f"henxels for {path or '<repo root>'}"]

    matched = [hx for hx in contract.henxels if _governs(path, hx)]
    if not matched:
        lines.append("  (no henxels apply here — the contract is silent)")
        return "\n".join(lines)

    for hx in matched:
        tag = " [warn]" if hx.level == "warn" else ""
        lines.append(f"  • {hx.text}{tag}")
        if hx.why:
            lines.append(f"      ↳ {' '.join(hx.why.split())}")
        for name, param in hx.statements.items():
            lines.append(f"      {name}: {_fmt(param)}")
    return "\n".join(lines)


def explain_data(contract: Contract, rel_path: str) -> dict:
    """Structured form of explain (for `--json` / agent tool integration)."""
    path = str(rel_path).replace("\\", "/").strip("/")
    return {
        "path": path,
        "henxels": [
            {"henxel": hx.text, "why": hx.why, "in": hx.locations, "level": hx.level, "statements": hx.statements}
            for hx in contract.henxels
            if _governs(path, hx)
        ],
    }


def _governs(path: str, hx) -> bool:
    if not any(loc.governs(path) for loc in parse_all(hx.locations)):
        return False
    exc = parse_all(hx.excludes) if hx.excludes else []
    return not any(e.matches(path) for e in exc)


def _fmt(param) -> str:
    if isinstance(param, list):
        return ", ".join(str(p) for p in param)
    return str(param)
