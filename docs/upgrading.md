---
title: Upgrading
summary: How henxels tells you about new versions, how to refresh a repo's local files after upgrading, and why schema changes never break an existing contract.
---

# Upgrading

## The version nag

`henxels check` and `henxels doctor` print a one-line notice to stderr when a newer version
is on PyPI:

```text
↑ henxels 0.6.0 is available (you have 0.5.5) — upgrade: uv tool upgrade henxels
  (or pipx/pip -U), then run `henxels init` to refresh hooks + schema
```

It is deliberately quiet: cached for a day, silent in CI and when offline, never blocking,
printed to stderr so machine-readable stdout stays clean, and never run inside the git
hooks. Turn it off with `HENXELS_NO_UPDATE_CHECK=1`. Because your installed version is
compared to PyPI, a local development checkout never nags itself.

## Refreshing a repo after upgrading

After you upgrade henxels, re-run `henxels init` in each repo:

```bash
uv tool upgrade henxels   # or pipx upgrade henxels
henxels init              # refresh local schema, git hooks, and the digest
```

`henxels init` is idempotent. It refreshes three things that evolve between versions — the
local `.henxels/henxels.schema.json` (editor autocomplete), the git hook scripts (their
resolution logic changes), and the `AGENTS.md` digest — and it leaves your `henxels.yaml`
and your hand-written `AGENTS.md` text untouched.

## Why schema changes don't break old contracts

The bundled JSON schema is only an **editor aid** — it never gates `henxels check`.
Validation runs against the registered statements, not the schema. The schema is also
permissive (it allows unknown keys), so:

- A **stale** local schema never breaks anything; it just won't autocomplete new keys.
- A **new** schema never rejects an older contract; changes are additive.

So refreshing is purely additive, and there's no migration dance. The only genuinely
breaking change is removing or renaming a statement, which is a real deprecation regardless
of the schema. A parity test in henxels' own suite keeps the schema in step with the
built-in statements, so the autocomplete can't silently fall behind.
