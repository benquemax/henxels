---
title: Getting started
summary: Install henxels, scaffold a contract, and validate your repo in three commands.
---

# Getting started

henxels gives your repository an external frame — a contract that says where things
belong — and keeps agents and humans inside it.

## Install and initialize

```bash
uvx henxels init        # zero-install via uv (or: pipx install henxels)
```

`henxels init` detects your stack, writes a commented `henxels.yaml`, installs the
teaching git hooks, and drops a contract digest into `AGENTS.md`.

### Start from a template

```bash
henxels init --template okf-llm-wiki    # an Open Knowledge Format wiki
```

Templates ride on top of the detected starter. `okf-llm-wiki` sets up an
[OKF](enforcing-okf.md) wiki two ways, depending on what it finds:

- **No wiki yet** — seeds `wiki/` (an index, one starter concept, an update log) so the
  contract holds from the first minute, with blocking rules: the wiki grows up inside
  them.
- **Existing wiki** — governs it without touching its content. The wiki rules start at
  `level: warn`, so the findings are a migration plan, not blocked commits; when
  `henxels check` runs clean, delete the `level: warn` lines to enforce.

The wiki lives at `wiki/` by default; say `--wiki-dir pages` to govern another folder.
If henxels spots markdown that might already be your wiki somewhere else, it stops and
asks rather than guessing — the error contains the exact command to rerun. Add
`--dry-run` to see what init would do without writing anything.

> **Using husky (or another `core.hooksPath` tool)?** git then looks for hooks there, not
> in `.git/hooks` where henxels installs — so henxels' hooks won't fire. `henxels init`
> warns when it detects this, and `henxels doctor` flags it instead of reporting a
> misleading green. To enforce: unset `core.hooksPath` (`git config --unset
> core.hooksPath`), or call `henxels _precommit` / `henxels _prepush` from your existing
> hooks.

A related gotcha is when git *finds* the hook but the hook can't find henxels:

> **Hook fails with `No module named henxels`?** The hook found a python but not henxels
> in it — common when henxels is an isolated `uv tool install` whose bin dir isn't on the
> hook's `PATH`, in a repo that isn't a Python project. Recent versions fall back to `uv
> tool run henxels` and, failing everything, print how to fix it instead of that opaque
> error. If you're on an older version, `henxels init` from an env where `henxels` is on
> `PATH` (or `uv tool install henxels`) rewrites the hook.

## Tailor the contract

Open `henxels.yaml` and shape the rule list to your repo. Each henxel is a sentence plus
statements; run `henxels catalogue` to see the statements you can use, and your editor
autocompletes them from the bundled schema.

## Validate

```bash
henxels check --all          # run every henxel
henxels explain src/foo.py   # what governs this spot, in plain words
```

To disobey a rule, change `henxels.yaml`. That is the only sanctioned escape — which
makes every deviation deliberate and visible in the diff.
