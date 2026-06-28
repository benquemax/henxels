# henxels × agent harnesses

henxels enforces your contract **two ways**, and the first one needs no integration:

1. **At git time, for every agent (and human).** The `pre-commit` / `pre-push` hooks
   `henxels init` installs run the contract, the delete/push guards, and your
   `run_before_commit` gates — no matter which harness made the change. This is the
   backbone; it already works everywhere.
2. **In the agent's loop (optional steering).** Before the agent writes a file, point
   its hook at henxels so it writes the right thing in the right place the first time.

The in-loop recipes are thin glue around three commands:

| command | use |
|---|---|
| `henxels explain <path>` (`--json`) | what governs this path — *steer before writing* |
| `henxels check <path>` | validate one file (exit 1 on violation) |
| `henxels check --staged` | validate the staged set |

> Wherever a recipe says `henxels`, use `uv run henxels` (or install it globally with
> `uv tool install henxels` / `pipx install henxels`) so the command is on PATH.

## Harness matrix

| Harness | In-loop mechanism | Recipe |
|---|---|---|
| **Claude Code** | `PreToolUse` / `PostToolUse` hooks | [`claude-code/`](claude-code/) |
| **OpenCode** | plugin `tool.execute.before` | `henxels integrate opencode` (or [`opencode/`](opencode/)) |
| **Aider** | `--lint-cmd` (runs after each edit) | [`aider/`](aider/) |
| **Hermes** | Agent Skill + command-approval + git hooks | [`skill/`](skill/) |
| **Pi** | Agent Skill / TypeScript extension + git hooks | [`skill/`](skill/) |
| **anything else** | the git hooks + AGENTS.md + a wrapper | [`generic/`](generic/) |

**Hermes and Pi** don't document a pre-tool callback, but both support **Agent Skills**
([agentskills.io](https://agentskills.io)) and read the project's `AGENTS.md`. So their
in-loop steering is the henxels **skill** in [`skill/`](skill/) plus the git-hook
backbone; for Hermes, also use its *command approval* to gate `git push`.

The honest summary: the git hooks give every harness hard enforcement for free. The
recipes here just make the agent aware *earlier*.
