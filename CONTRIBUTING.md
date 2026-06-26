# Contributing to henxels

henxels is a **framework + a community standard library of checks**. The maintainer
keeps the framework sharp and maintains his own checks — the *library* grows because
people contribute the reusable building blocks they write. That's the whole engine of
the project. Thank you for adding to it.

> **We're in the agentic era: send a ready-to-merge PR, not an issue.** If you (or your
> agent) wrote a check that would help others, contribute it. If you found a bug,
> fixing it in a PR is worth ten issues describing it.

## Two kinds of check — know which you have

- **Reusable statement** → contribute it. It's general: it doesn't hardcode *your*
  repo's folder names or paths, and it would be useful in other projects
  (e.g. `max_lines`, `no_print_statements`, `frontmatter_has`).
- **Ad-hoc statement** → keep it local in your `henxels_checks.py`. It's specific to
  your repo (e.g. `legacy_is_gone_or_tidy_markdown_archive`). Perfectly fine — just
  not a library building block.

Run `henxels contribute <name>` and it'll tell you which you have and the next step.

## The bar for a built-in statement

A statement that ships with henxels must be:

1. **General** — no project-specific names, paths, or assumptions.
2. **Well-named** — the name reads as part of a sentence (`casing`, `forbidden_files`).
3. **Self-describing** — a `help="…"` one-liner (shown in `henxels catalogue`).
4. **Boilerplate-free** — arguments injected by name (`param`, `scope`, `file`, …);
   ask only for what you use; name `file` for per-file checks.
5. **Instructive on failure** — return a **string instruction** (or list) telling the
   agent *what to do*, not a bare `False`. None/True means pass.
6. **Tested** — a focused test in `tests/test_statements.py`.
7. **Clean** — passes `ruff` and the full suite.

## How to add one

```bash
# 1. add your function to henxels/statements/builtins.py, e.g.
#    @statement("max_lines", help="source files stay under a line budget", builtin=True)
#    def max_lines(param, file, scope):
#        if scope.line_count(file) > param:
#            return f"split {file} — keep under {param} lines"
# 2. add a test in tests/test_statements.py
# 3. document it in the JSON schema ($defs/henxel/properties) so editors autocomplete it
# 4. run the gates (they also run in pre-commit + CI):
uv run ruff check .
uv run pytest -q
uv run henxels check --all
# 5. open the PR — https://github.com/benquemax/henxels
```

The quality gates are enforced by henxels' own contract (`run_before_commit`) and CI,
so a green local run means your PR is **merge-ready**. That's the goal: no round-trips.

## Conventions

- Python ≥ 3.10, standard library first; new third-party deps need a clear reason.
- Keep statements pure verifications: detect and instruct; never mutate files.
- Match the surrounding style; `ruff` is the arbiter.
- A henxel is a *rule*; a statement is the *reusable predicate*. Don't blur them.
