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

    matched = [hx for hx in contract.henxels if _path_in(path, hx.locations)]
    if not matched:
        lines.append("  (no henxels apply here — the contract is silent)")
        return "\n".join(lines)

    for hx in matched:
        tag = " [warn]" if hx.level == "warn" else ""
        lines.append(f"  • {hx.text}{tag}")
        for name, param in hx.statements.items():
            lines.append(f"      {name}: {_fmt(param)}")
    return "\n".join(lines)


def _path_in(path: str, locations: list[str]) -> bool:
    return any(loc.governs(path) for loc in parse_all(locations))


def _fmt(param) -> str:
    if isinstance(param, list):
        return ", ".join(str(p) for p in param)
    return str(param)
