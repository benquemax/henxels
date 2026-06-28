"""Materialize a harness integration into the user's project.

So an agent (or a human) installs the OpenCode staging guard with one command —
`henxels integrate opencode` — instead of hand-copying a JS file. The integration
files ship inside the package (henxels/integrations/), so this works from any install.
"""

from __future__ import annotations

from pathlib import Path

_SOURCE = Path(__file__).parent / "integrations"

# harness -> where its integration file lands in the project
DESTINATIONS = {
    "opencode": ".opencode/plugins/henxels.js",
}


def available() -> list[str]:
    return sorted(DESTINATIONS)


def write_integration(harness: str, root: Path | str) -> tuple[Path, str]:
    if harness not in DESTINATIONS:
        raise ValueError(f"unknown harness {harness!r}; choose from {', '.join(available())}")
    src = _SOURCE / f"{harness}.js"
    dest = Path(root) / DESTINATIONS[harness]
    existed = dest.exists()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return dest, ("updated" if existed else "created")
