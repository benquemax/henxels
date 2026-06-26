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
    in: docs
    files_are: .md
    casing: kebab-case
    frontmatter_has: title
```

## Statements

Run `henxels catalogue` to see the built-in standard library. A few:

- **casing** — file names use a convention (`snake_case`, `kebab-case`, …).
- **files_are** — every file is an extension or glob (a list means *any of*).
- **frontmatter_has** — markdown declares these keys (a list means *all*).
- **forbidden_files / forbidden_folders** — none of these may exist.
- **required_files / required_folders** — these must exist.
- **run_before_commit / run_before_push** — a command (tests, lints) must pass.

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
