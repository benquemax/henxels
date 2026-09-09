---
title: Upgrading
summary: How henxels tells you about new versions, how to refresh a repo's local files after upgrading, why a stale local schema now nags, and why schema changes never break an existing contract.
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

## The stale-schema nag

Forgetting that re-run used to be silent, and it misleads people. `.henxels/henxels.schema.json`
is a **committed artifact**: it keeps documenting the feature set of whichever version
last wrote it. Upgrade the tool without re-running `init`, and the repo advertises the old
schema while the tool happily supports more. Anyone reading the artifact — a teammate, an
agent diagnosing a config question — concludes a key isn't supported when it is. That is a
documentation artifact lying about a capability that already works.

So henxels now checks the copy against the running version, in three places:

```text
⚠ .henxels/henxels.schema.json predates the installed henxels (0.15.0)
    a schema older than the tool hides knobs that already work — readers trust
    the committed artifact over the binary
    → henxels init   (or `henxels sync`) — then commit the refreshed schema
```

- **`henxels sync`** now refreshes the local schema as well as the digest, so the ordinary
  "keep my repo current" command closes the loop. It only touches a copy the repo already
  keeps — sync never conjures `.henxels/` into a repo that deliberately has none.
- **`henxels sync --check`** reports the drift without writing and exits 1.
- **pre-commit** warns (loudly, never blocking), and **`henxels doctor`** shows it as a check.

This is a different nag from the version notice above. That one says *your tool is behind*;
this one fires when your tool is current and your repo's copy of its documentation is not.
The version nag also disappears the moment versions match — which is exactly when the stale
artifact is left behind unnoticed.

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

The nag above is therefore about **truthfulness, not safety**: a stale copy never breaks a
run, it just misinforms whoever reads it.
