---
title: Writing henxels
summary: A henxel is a sentence plus statements that must all pass; statements are reusable functions you can extend.
---

# Writing henxels

A **henxel** is one rule on the whiteboard: a sentence (which is also the failure
message), an optional `in:` scope, and one or more **statements** that must all pass.
A statement is a named function with parameters.

```yaml
henxels:
  - henxel: "Docs are kebab-case markdown with a title"
    in: ./docs                 # direct files; use ./docs/* for subfolders too
    allowed_filetypes: .md
    filename_casing: kebab-case
    required_frontmatter: title
```

## Scoping with `in:`

Paths are anchored at the repo root, and recursion is explicit via a trailing `*`:

- `./docs` — files **directly in** docs/ (this level only)
- `./docs/*` — docs/ **and all subfolders**
- `./` — the repo root; `./*` — the whole repo (the default when `in:` is omitted)

## Statements

Run `henxels catalogue` to see the built-in standard library. A few:

- **filename_casing** — file names use a convention (`snake_case`, `kebab-case`, …).
- **allowed_filetypes** — every file is an extension or glob (a list means *any of*).
- **required_frontmatter** — markdown declares these keys (a list means *all*).
- **forbidden_files / forbidden_subfolders** — none of these may exist.
- **required_files / required_subfolders** — these must exist.
- **run_before_commit / run_before_push** — a command (tests, lints) must pass.
- **markdown_lint** — markdown files pass pymarkdownlnt (rules tuned in `[tool.pymarkdown]`).
- **well_formed_statements** — your custom statements have a `help=` and a test.

Scalars stand in for one-item lists, so you never write `[x]`.

## Custom statements

Missing a check? Write one — it's three lines, auto-loaded from `henxels_checks.py`:

```python
from henxels import statement

@statement("max_lines", help="source files stay under a line budget")
def max_lines(param, file, scope):
    if scope.line_count(file) > param:
        return f"split it — keep under {param} lines"
```

Arguments are injected by name; return a string instruction to fail. If your statement
is reusable beyond this repo, contribute it: `henxels contribute`.
