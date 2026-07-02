---
title: henxels documentation
summary: Map of the henxels guides — the contract, built-in and custom checks, settings, guards, agent integrations, and upgrading.
---

# henxels documentation

henxels is a repo-level harness: a contract (`henxels.yaml`) of file-level rules that
keep agents and humans true to your repo's structure. These guides go deeper than the
[README](../README.md).

## Guides

- [Getting started](getting-started.md) — install, initialize, validate.
- [Writing henxels](writing-henxels.md) — the contract: a henxel, `in:`, `except:`,
  `level:`, and `why:`.
- [Built-in statements](built-in-statements.md) — the standard library, by category.
- [Custom checks](custom-checks.md) — write your own statements: where they live, how
  they're named, and the injection API.
- [Settings](settings.md) — behaviours: staging, push, delete, similarity, large files.
- [Guards and bless](guards-and-bless.md) — how the push and delete protections work.
- [Agent integrations](agent-integrations.md) — the `AGENTS.md` digest and harness hooks.
- [Enforcing OKF](enforcing-okf.md) — a worked contract for the Open Knowledge Format:
  keep an agent-maintained wiki conformant.
- [Upgrading](upgrading.md) — the version nag, refreshing local files, schema evolution.

## The shape of it

A **henxel** is one rule: a sentence (also the failure message), an optional `in:` scope,
and **statements** that must all pass. A **statement** is a named verification function —
the reusable, extensible unit. `settings:` holds **behaviours** (push, delete, and staging
protections, similarity and large-file warnings) — the things that aren't tests.

To disobey a rule you edit `henxels.yaml`. That is the only sanctioned escape, which makes
every deviation deliberate and visible in the diff.
