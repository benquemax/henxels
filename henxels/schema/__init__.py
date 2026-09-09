"""Bundled JSON Schema for ``henxels.yaml`` (editor autocomplete + validation).

The schema also gets *copied into a repo* by ``henxels init`` (``.henxels/``), so
editors resolve it offline and in private repos. That copy is a committed artifact,
and artifacts rot: upgrade the tool and the repo keeps the schema of whatever version
it was init'd with. A key the tool fully supports then looks unsupported to whoever
reads the committed copy — human or agent. Hence ``local_schema_state``: the read-only
freshness check that lets sync, the pre-commit hook and doctor say so out loud.
"""

from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("henxels.schema.json")

# Where ``henxels init`` writes the repo-local copy (also re-exported by scaffold,
# which owns the rest of the init layout).
LOCAL_SCHEMA_PATH = ".henxels/henxels.schema.json"


def schema_text() -> str:
    return SCHEMA_PATH.read_text(encoding="utf-8")


def local_schema_path(root: Path | str) -> Path:
    return Path(root) / LOCAL_SCHEMA_PATH


def local_schema_state(root: Path | str) -> str:
    """Report the repo-local schema copy as "missing", "fresh" or "stale".

    "missing" is not drift — a repo that keeps no local copy made a choice, and
    nagging it would be noise. Comparison is on stripped text so line-ending and
    final-newline churn never masquerades as a stale schema; a copy that no longer
    matches the bundled one (including an unparseable one) is stale.
    """
    path = local_schema_path(root)
    if not path.is_file():
        return "missing"
    try:
        current = path.read_text(encoding="utf-8")
    except OSError:
        return "stale"
    return "fresh" if current.strip() == schema_text().strip() else "stale"


def refresh_local_schema(root: Path | str) -> str:
    """Write the bundled schema into the repo; report created/updated/unchanged.

    "unchanged" is load-bearing: a refresh that rewrote the file every time would
    dirty the worktree on every sync, and a spurious diff is a diff people learn to
    stage blindly.
    """
    state = local_schema_state(root)
    if state == "fresh":
        return "unchanged"
    path = local_schema_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(schema_text(), encoding="utf-8")
    return "created" if state == "missing" else "updated"
