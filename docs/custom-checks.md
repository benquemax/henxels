---
title: Custom checks
summary: Write your own statements — where the files live, how statements are named and invoked, the injection API, and how henxels guards against reinventing a built-in.
---

# Custom checks

When no built-in fits, you write a **statement** — a small Python function henxels calls
to verify one thing. Before you do, run `henxels catalogue` and check there isn't already
a built-in for it (see [Built-in statements](built-in-statements.md)). Reinventing a
built-in is the most common mistake.

## Where custom checks live

henxels auto-loads custom statements from three places, all relative to the repo root
(where `henxels.yaml` lives):

- **`henxels_checks.py`** at the repo root — the default, loaded with no config.
- **`.henxels/*.py`** — any `.py` file in the `.henxels/` folder, so you can split checks
  across files (`.henxels/wiki_checks.py`, `.henxels/routine_checks.py`). Files whose name
  starts with `_` are skipped, so `.henxels/_helpers.py` is treated as a helper, not a
  check module. (This is the same `.henxels/` that holds the editor schema; the `.json` is
  ignored for loading.)
- **A module under `imports:`** in `henxels.yaml`, for an unusual path or an installed
  package:

```yaml
imports:
  - tools/my_checks.py
```

Commit these files. A custom check is contract logic that CI and teammates need, exactly
like `henxels.yaml` itself.

## How a statement is named and used

The name you use in `henxels.yaml` is the **string passed to `@statement(...)`** — the
function's own name is irrelevant.

```python
from henxels import statement

@statement("routine_list_format", help="routine files have a '# Routines' heading and '*' bullets")
def whatever_you_call_it(file, scope):
    ...
```

Use it as a statement key in a henxel, just like a built-in:

```yaml
  - henxel: "Routine files are well-formed"
    in: ./routines/*
    routine_list_format: true
```

Name it in snake_case (it's a YAML key), make it descriptive, and **never reuse a built-in
or settings name** — henxels will warn and ignore it (see "The collision guard" below).
`henxels create-new-statement <name>` scaffolds a correctly-shaped stub for you.

## The injection API

Arguments are injected **by name** — declare only the ones you need, in any order:

- **`param`** — the value from the contract (`8000` for `max_lines: 8000`; a list or dict
  if you pass one).
- **`scope`** — the context: `scope.files` (paths in scope), `scope.read_text(f)`,
  `scope.line_count(f)`, `scope.exists(rel)`, `scope.is_dir(rel)`, `scope.all_files`,
  `scope.root`, `scope.settings`.
- **`file`** — opt into **per-file mode**: henxels runs your function once per file in
  scope, passing each path.
- **`root`** — the repo root, as a `Path`.
- **`settings`** — the contract's `settings:` dict.
- **`diff`** — the staged diff at commit time (else `None`). Use it for rules about
  *change*: `diff.modified`, `diff.added`, `diff.deleted`, `diff.old_text(f)`,
  `diff.new_text(f)`. See `append_only` / `bump_updated_on_change` for examples.

## What to return

A statement returns its violations as **instructions**, so the output is actionable:

- `None` or `True` — pass.
- a **string** — fail; the string is the instruction shown to the agent.
- a **list of strings** — fail with several instructions.
- `False` — fail, falling back to the henxel's own sentence as the instruction.

```python
from henxels import statement

@statement("max_lines", help="source files stay under a line budget")
def max_lines(param, file, scope):              # asks for `file` → per-file mode
    if scope.line_count(file) > param:
        return f"split {file}: keep it under {param} lines"
```

## The collision guard

A custom check **cannot silently replace a built-in**. If you register a statement with a
built-in's name, the built-in is kept and yours is ignored — and `henxels check` and
`henxels doctor` warn you. They also flag a custom check that uses a **settings** name
(like `warn_about_large_files`), which means you reinvented a behaviour that belongs under
`settings:`. The fix is always to use the built-in or the setting.

## Contributing

If your check is reusable — useful in other repos, not tied to yours — contribute it
upstream so it becomes a built-in: `henxels contribute <name>`. The bar is a `help=`
description and a test (`well_formed_statements` enforces it).
