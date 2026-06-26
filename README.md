<!-- markdownlint-disable -->
```
   ╭───────────────╮
   │  ╷  ╷   ╷  ╷  │   h e n x e l s
   │  ╵‖ ╵   ╵ ‖╵  │   suspenders for your repo
   │   ‖       ‖   │   keep your ADHD agent in henxels
   ╰───────────────╯
```
<!-- markdownlint-enable -->

# henxels

**A repo-level harness for coding agents** — file-level rules that steer agents (and
humans) to keep a repository true to a contract. Each rule is a *henxel* (from Finnish
_henkselit_, "suspenders").

Most agent harnesses wrap the *agent*. henxels is a harness that lives in the *repo*: a
structural contract that holds **every** agent — Claude Code, OpenCode, Aider, Hermes,
Pi, or a human — to the same shape, no matter which one made the change.

henxels is for repos where small, eager, easily-distracted coding agents keep writing
the right thing in the wrong place. It puts the expected structure **in front of the
agent** (in `AGENTS.md` and on demand) and makes breaking it **impossible by accident**:
to disobey a henxel you must change the contract — a conscious, reviewable act.

Under the hood henxels is **a framework + a growing community library of checks**:
the contract just lists which checks apply where; the checks are functions, and you can
add your own in three lines.

---

## The contract reads like a whiteboard

`henxels.yaml` is a list of rules. Each **henxel** is a sentence (which doubles as the
failure message) plus the **statements** that must all pass. Logic lives inside the
statements, so the YAML stays a dumb, readable list.

```yaml
settings:                      # behaviours, not tests
  ask_me_before_staging: true
  confirm_before_push: true
  confirm_before_deleting: { over_lines: 5 }

henxels:
  - henxel: "Docs are kebab-case markdown, each with a title and summary"
    in: ./docs                 # ./docs = this level; ./docs/* = recursive
    allowed_filetypes: .md     # a scalar; lists are OR: [.md, .txt]
    filename_casing: kebab-case
    required_frontmatter: [title, summary]   # a list here is AND: both required

  - henxel: "Project config lives only in pyproject.toml"
    forbidden_files: [setup.py, setup.cfg]   # no `in:` = whole repo

  - henxel: "The test suite passes before every commit"
    run_before_commit: "uv run pytest -q"
```

Browse every statement you can use with **`henxels catalogue`**.

---

## Principles

1. **The contract is the single source of structural truth.** If it isn't in
   `henxels.yaml`, it isn't a rule.
2. **Read it like a document.** A human — or a small model — understands the repo's
   shape without reading a validator.
3. **A henxel is a test that must pass.** Logic hides in the statement functions; the
   YAML just lists them. Failure returns an *instruction*, not a bare boolean.
4. **Steer before you stop.** Every henxel says, in words, what to do instead.
5. **Disobey responsibly.** The only escape hatch is editing the contract.
6. **Awareness beats blocking** — especially for duplication.
7. **Beautiful for humans, silent for machines.** Fancy in a terminal, plain in a pipe.

---

## Quick start

### Install

```bash
uv tool install henxels      # puts `henxels` on your PATH (recommended)
# alternatives:
#   pipx install henxels     # same idea, via pipx
#   uvx henxels <cmd>        # zero-install, run on demand
#   npm i -g henxels         # node-friendly launcher (shims to Python)
```

> If henxels lives only inside a project venv, invoke it as `uv run henxels …`. The git
> hooks resolve it either way, and henxels' own messages always print the form that
> works in your shell.

### Give this to your agent

> Install henxels (`uv tool install henxels`, or `pipx install henxels`, or
> `npm i -D henxels` — it shims to Python; install a prerequisite if one's missing).
> Run `henxels init`, then tailor `henxels.yaml` to this repo's folders (run
> `henxels catalogue` to see the statements), and run `henxels sync` and
> `henxels check --all`.

### Or yourself

```bash
henxels init            # scaffold contract + git hooks + AGENTS.md digest
henxels catalogue       # browse the statements you can use
henxels explain docs/x.md   # what governs this path?
henxels check --all     # run the contract
```

---

## Custom checks in three lines

Need a check that doesn't exist? Write a statement. Drop it in `henxels_checks.py` at
the repo root (auto-loaded — no config) and use it like any built-in.

```python
from henxels import statement

@statement("max_lines", help="source files stay under a line budget")
def max_lines(param, file, scope):        # asks for `file` → per-file, no loop
    if scope.line_count(file) > param:
        return f"split it — keep under {param} lines"   # fail = the instruction itself
```
```yaml
  - henxel: "No source file exceeds 500 lines"
    in: ./src/*
    max_lines: 500
```

Arguments are injected by name (`param`, `scope`, `file`, `root`, `settings`) — take
only what you need. Return `None`/`True` to pass, or a string instruction to fail.

---

## Example: keeping an LLM wiki from scattering

An **LLM wiki** — a markdown knowledge base an agent reads and writes (the pattern
popularized by Andrej Karpathy) — is a perfect henxels use case. The idea is great, but
small models drift hard: they write against the conventions, and knowledge that belongs
in **one** page ends up **scattered across several near-duplicate files**. henxels gives
the wiki a structure the agent has to follow, and warns it the moment it's about to
fragment a topic.

```yaml
settings:
  confirm_before_deleting: { over_lines: 10 }    # don't lose knowledge to a diff slip
  warn_about_similar_files:                        # the anti-scatter henxel: nudges the
    above: 0.82                                    # agent to UPDATE a page, not clone it
    ignore: ["**/index.md"]

henxels:
  - henxel: "Every wiki page is kebab-case markdown with findable metadata"
    in: ./pages/*
    filename_casing: kebab-case
    allowed_filetypes: [.md]
    required_frontmatter: [title, tags, updated]
  - henxel: "Pages are clean markdown with no dead links"
    in: ./pages/*
    markdown_lint: true
    links_resolve: true          # a custom check (see "Custom checks" above)
  - henxel: "The wiki has a single index"
    in: ./pages
    required_files: index.md
```

Because the contract is mirrored into `AGENTS.md`, the agent reads *"one page per topic,
kebab-case, with these fields"* **before** it writes — and `warn_about_similar_files`
catches it when it's about to create the fifth slightly-different page about the same
thing. Strong guidance is exactly what small LLMs need to stay tidy.

---

## Ouroboric by design

henxels eats its own tail, and it's the better for it. Its own repo is governed by its
own `henxels.yaml`, so every feature is dogfooded on the tool before it ships.
`well_formed_statements` is a check that checks the checks. `markdown_links_absolute`
guards the README that documents henxels. The pre-commit hook runs `henxels check` —
henxels gating henxels. The contract even mirrors itself into `AGENTS.md` to steer the
agent that edits the contract.

The tail-eating *is* the test.

---

## Guards & bless

`settings` can guard hard-to-undo actions. They don't forbid — they make you mean it:

```text
$ git push
✗ Push is guarded — a push is hard to take back
    → henxels bless push   (then push again)
```

`henxels bless push` mints a one-time token bound to the exact commit. The delete guard
covers deleted files **and** net-removed lines (diff-edit mistakes lose rows), released
by `henxels bless delete`.

---

## Contributing — the agentic era

henxels thrives on contributions. **We'd rather get a ready-to-merge PR than an issue.**
If you (or your agent) write a check that's *reusable* — general, not tied to your repo —
contribute it upstream: `henxels contribute`. Quality gates (ruff + the test suite) run
in pre-commit and CI, so a green local run means your PR is merge-ready. See
[`CONTRIBUTING.md`](https://github.com/benquemax/henxels/blob/main/CONTRIBUTING.md).

---

## Commands

| Command | Purpose |
|---------|---------|
| `henxels init` | scaffold contract + hooks + digest |
| `henxels check [--all\|--staged] […]` | run the contract |
| `henxels explain <path>` | what governs this location |
| `henxels catalogue` | browse the statements you can use |
| `henxels create-new-statement <name>` | scaffold a custom statement |
| `henxels contribute [name]` | how to upstream a reusable statement |
| `henxels bless <push\|delete>` | consciously override a guard |
| `henxels sync` / `henxels doctor` | refresh the digest / check the setup |

## License

MIT.
