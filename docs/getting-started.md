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

> **Using husky (or another `core.hooksPath` tool)?** git then looks for hooks there, not
> in `.git/hooks` where henxels installs — so henxels' hooks won't fire. `henxels init`
> warns when it detects this, and `henxels doctor` flags it instead of reporting a
> misleading green. To enforce: unset `core.hooksPath` (`git config --unset
> core.hooksPath`), or call `henxels _precommit` / `henxels _prepush` from your existing
> hooks.

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
