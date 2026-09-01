"""Meta statements: keep the statement library itself merge-ready."""

from __future__ import annotations

import inspect
from pathlib import Path

from henxels.statements.registry import all_statements, statement


@statement(
    "well_formed_statements",
    help="statements defined in this repo carry a help= description and have a test",
    builtin=True,
)
def well_formed_statements(scope):
    """Dogfoodable quality bar for statement code.

    Checks every statement whose source lives *in this repo* (the built-ins when run
    on henxels itself; your custom statements when run on your repo) — they must have
    a one-line ``help=`` and be exercised by a test. The library grows on
    contributions, so this keeps them merge-ready.
    """
    root = scope.root.resolve()
    # Repo-wide question, so read the repo — not scope.all_files, which in a git repo
    # is only the *staged* files. Trusting it made every statement look untested
    # whenever the commit happened not to stage its test.
    from henxels.engine.discover import discover

    test_text = "\n".join(
        scope.read_text(f) or ""
        for f in discover(root)
        if f.rsplit("/", 1)[-1].startswith("test_") or f.startswith("tests/") or "/tests/" in f
    )
    violations = []
    for name, sdef in sorted(all_statements().items()):
        source = inspect.getsourcefile(sdef.fn)
        if not source or not _within(Path(source), root):
            continue  # defined outside this repo (e.g. the installed library)
        rel = Path(source).resolve().relative_to(root).as_posix()
        if rel.startswith("tests/") or "/tests/" in rel or Path(source).name.startswith("test_"):
            continue  # test fixtures aren't contributions
        if not sdef.help:
            violations.append(f"statement '{name}' — add a help= description (shown in `henxels catalogue`)")
        if name not in test_text:
            violations.append(f"statement '{name}' — add a test that exercises it")
    return violations


def _within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root)
        return True
    except ValueError:
        return False
