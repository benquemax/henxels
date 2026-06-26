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

## Tailor the contract

Open `henxels.yaml` and shape the `tree:` to your real folders. Each rule carries a
plain-language `reason` and `steer`, so the contract reads like a document and your
editor autocompletes the enum values from the bundled schema.

## Validate

```bash
henxels check --all     # everything
henxels explain src/foo.py   # what governs this spot, in plain words
```

To disobey a rule, change `henxels.yaml`. That is the only sanctioned escape — which
makes every deviation deliberate and visible in the diff.
