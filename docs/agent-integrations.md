---
title: Agent integrations
summary: How henxels reaches agents — the AGENTS.md digest every agent reads, and per-harness hooks (with self-installing OpenCode enforcement).
---

# Agent integrations

henxels enforces your contract two ways, and the first needs no integration.

## The git hooks (every agent and human)

`henxels init` installs `pre-commit` and `pre-push` hooks that run the contract, the
guards, and your command gates — no matter which harness made the change. This is the
backbone; it already works everywhere. See [Guards and bless](guards-and-bless.md).

## The AGENTS.md digest (steering)

henxels mirrors the contract into a managed block in `AGENTS.md`, between
`<!-- henxels:begin -->` and `<!-- henxels:end -->`. Agents read it before they write, so
they put the right thing in the right place the first time. Your hand-written text outside
the markers is never touched. Refresh it with `henxels sync` (and `henxels init` regenerates
it too). When `ask_me_before_staging` is set, the digest leads with a prominent
"don't `git add` / commit / push — ask the user" directive.

## In-loop harness hooks

Before an agent writes a file, point its hook at henxels so it sees what governs the spot.
The recipes are thin glue around three commands:

- `henxels explain <path>` — what governs this path (add `--json` for tooling).
- `henxels check <path>` — validate one file (exit 1 on a violation).
- `henxels check --staged` — validate the staged set.

The harness matrix and ready-to-use recipes live in the repo's `integrations/` folder
(Claude Code, OpenCode, Aider, Hermes/Pi via Agent Skills, and a generic wrapper).

## OpenCode: self-installing enforcement

OpenCode can do more than steer. Install the plugin with one command — the agent can run
it itself:

```bash
henxels integrate opencode
```

This writes `.opencode/plugins/henxels.js`, which adds a `tool.execute.before` guard that
**hard-blocks** `git add` / `git commit` when the contract sets `ask_me_before_staging`
(push stays guarded by the pre-push hook), and a `tool.execute.after` hook that runs
`henxels check` on each edited file. When the digest is current, it tells OpenCode agents
to run `henxels integrate opencode`, so setup is delegated to the agent, not you.
