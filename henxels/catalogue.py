"""Discoverability + contribution: browse statements, scaffold new ones, upstream them.

The framework grows by contribution, so reuse must be easy (`catalogue`), authoring
must be boilerplate-free (`create-new-statement`), and contributing a reusable one
must be a single nudge (`contribute`).
"""

from __future__ import annotations

from pathlib import Path

from henxels.statements.registry import all_statements

LOCAL_CHECK_FILE = "henxels_checks.py"


def render_catalogue() -> str:
    stmts = all_statements()
    builtin = sorted((d for d in stmts.values() if d.builtin), key=lambda d: d.name)
    custom = sorted((d for d in stmts.values() if not d.builtin), key=lambda d: d.name)

    lines = ["henxels catalogue — statements you can use inside a henxel", ""]
    lines.append("Built-in (the standard library):")
    for d in builtin:
        lines.append(f"  {d.name:<20} {d.help}{_flags(d)}")
    if custom:
        lines += ["", "Custom (loaded from this repo):"]
        for d in custom:
            lines.append(f"  {d.name:<20} {d.help or '(no description)'}{_flags(d)}")
    lines += [
        "",
        "Reuse before reinventing. Missing one?  henxels create-new-statement <name>",
        "Reusable beyond this repo?  henxels contribute  (send a ready-to-merge PR)",
    ]
    return "\n".join(lines)


def _flags(d) -> str:
    bits = []
    if d.per_file:
        bits.append("per-file")
    if d.stage:
        bits.append(d.stage)
    return f"  [{', '.join(bits)}]" if bits else ""


def create_statement_scaffold(name: str, root: Path | str) -> tuple[Path, str]:
    """Append a template statement to henxels_checks.py. Returns (path, 'created'|'updated')."""
    root = Path(root)
    func = _identifier(name)
    path = root / LOCAL_CHECK_FILE
    existed = path.is_file()
    body = "" if existed else "from henxels import statement\n"
    body += _TEMPLATE.format(name=name, func=func)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(body)
    return path, ("updated" if existed else "created")


def contribute_guide(name: str | None = None) -> str:
    lines = [
        "Contributing a statement upstream (the project thrives on this):",
        "",
        "Is it REUSABLE — useful in other repos, not tied to this one's names/paths?",
        "  • Yes → upstream it as a built-in. Send a ready-to-merge PR (not an issue):",
        "      1. add the function to henxels/statements/builtins.py with builtin=True",
        "         and a clear help= string;",
        "      2. add a test in tests/test_statements.py;",
        "      3. run the gates locally (lint + tests must pass — PRs arrive merge-ready);",
        "      4. open the PR at https://github.com/benquemax/henxels",
        "  • No (ad-hoc to this repo) → keep it local in henxels_checks.py.",
    ]
    if name:
        stmt = all_statements().get(name)
        if stmt and not stmt.builtin:
            lines += ["", f"`{name}` is a custom statement — a good contribution candidate."]
        elif stmt and stmt.builtin:
            lines += ["", f"`{name}` is already built-in."]
    return "\n".join(lines)


def contribute_snippet(name: str) -> tuple[str, str] | None:
    """For a local custom statement, return (builtin-ready source, test stub)."""
    import inspect

    sdef = all_statements().get(name)
    if not sdef or sdef.builtin:
        return None
    try:
        source = inspect.getsource(sdef.fn).rstrip()
    except (OSError, TypeError):
        source = f"# (could not read the source of {name})"
    func = _identifier(name)
    test_stub = (
        f"def test_{func}(tmp_path):\n"
        f"    # TODO: build a Scope and assert `{name}` returns the right instruction(s)\n"
        f"    ..."
    )
    return source, test_stub


def _identifier(name: str) -> str:
    out = "".join(c if c.isalnum() else "_" for c in name).strip("_")
    return out or "my_check"


_TEMPLATE = '''

@statement("{name}", help="TODO: one-line description")
def {func}(param, file, scope):
    """TODO: explain what this checks.

    Args are injected by name — keep only what you need:
      param     the value from the contract (e.g. 500 for `{name}: 500`)
      file      asking for `file` makes this PER-FILE (henxels loops for you)
      scope     scope.files, scope.read_text(f), scope.line_count(f), scope.exists(p)

    Return None/True to pass, or a STRING INSTRUCTION (shown to the agent) to fail.

    Reusable beyond this repo? `henxels contribute {name}`.
    """
    # if <something is wrong with `file`>:
    #     return "do X instead"
    return None
'''
