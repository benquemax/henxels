---
title: Writing henxels
summary: The rule vocabulary — forbid, require, naming, canonical, guards, similarity — and how the closest rule wins.
---

# Writing henxels

A *henxel* is one rule in the contract. The closest rule in the tree governs a path,
and rules cascade into subfolders.

## The vocabulary

- **forbid** — a kind of file may not live in this folder subtree. Give a `reason`
  and a `steer` so the agent knows where it should go instead.
- **require** — this folder (or the repo root) must contain a named file. Add
  `severity: warn` for things that should exist locally but may be absent in CI.
- **naming** — files here follow a convention: `snake_case`, `kebab-case`,
  `camelCase`, `PascalCase`, `SCREAMING_SNAKE_CASE`, or `any`.
- **canonical** — a role lives in exactly one file; look-alikes are forbidden.
- **guards** — `push`, `delete`, and `stage` turn destructive reflexes into a
  conscious act (override once with `henxels bless`).
- **similarity** — warns when a new file looks like a near-copy of a committed one.

## Checks at commit time

Wire your test suite into the contract so the pre-commit hook runs it:

```yaml
checks:
  pre_commit:
    - "uv run pytest -q"
```

The contract stays the single source of truth — even the test gate lives there.
