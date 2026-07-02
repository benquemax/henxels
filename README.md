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

The flagship recipe is the **LLM wiki**: a markdown knowledge base that agents read and
write, kept true to Google's Open Knowledge Format
([OKF example below](#example-an-okf-open-knowledge-format-contract-for-your-llm-wiki)).
But any repo a model touches — code, docs, data — can be put in henxels.

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

Henxels can be installed by your agent or by you manually.

### Agentic instructions

Paste this to your coding agent:

> Install henxels (`uv tool install henxels`, or `pipx install henxels`, or
> `npm i -g henxels` — it shims to Python; install a prerequisite if one's missing).
> Run `henxels init`, then tailor `henxels.yaml` to this repo's folders (run
> `henxels catalogue` to see the statements), and finish with `henxels sync` and
> `henxels check --all`. Before writing any custom check, run `henxels catalogue` and use
> the built-in that fits — don't reinvent one, and never name a check after a built-in or a
> setting. Then commit (or ask the user to) `henxels.yaml`, `AGENTS.md`, and `.henxels/` —
> they're the contract; **don't gitignore `.henxels/`**. Also add a short "install
> henxels" line to the repo's README — the committed contract assumes the tool is
> installed, so contributors and CI need to know to get it.

### Manual instructions

```bash
uv tool install henxels   # or: pipx install henxels · uvx henxels · npm i -g henxels
henxels init              # scaffold contract + git hooks + AGENTS.md digest
henxels catalogue         # browse the statements you can use
henxels check --all       # run the contract
git add henxels.yaml AGENTS.md .henxels/   # commit your contract (see note below)
# then add an "install henxels" line to your README — the contract assumes it's installed
```

Building an **LLM wiki**? `henxels init --template okf-llm-wiki` sets up an
[Open Knowledge Format](https://github.com/benquemax/henxels/blob/main/docs/enforcing-okf.md)
wiki instead — seeded from scratch or governing the one you already have.

> **Commit `.henxels/`, don't gitignore it.** It holds the JSON schema your editor uses
> for autocomplete (your `henxels.yaml` points at it) and any custom checks you add — and
> custom checks are contract logic that CI and teammates need. After upgrading henxels,
> re-run `henxels init` to refresh the local schema, git hooks, and digest (it leaves your
> `henxels.yaml` untouched).
>
> If henxels lives only inside a project venv, invoke it as `uv run henxels …` — the git
> hooks resolve it either way.

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

## Tips & tricks

### Explain the *why*, not just the rule

A henxel's sentence says **how** the structure must be; a **`why:`** (aliases `context:` /
`comment:`) says *why it exists and how the thing it governs should be used*. It isn't a
test — it rides into `AGENTS.md`, so the agent reads the **purpose** of your structure,
not just the constraint. This is some of the cheapest, highest-leverage steering you can
give a small model.

```yaml
  - henxel: "_now, _next, _later exist in roadmap"
    in: ./roadmap
    required_subfolders: [_now, _next, _later]
    why: "The roadmap is planned now -> next -> later; route each new item into its bucket."
```

### Make an exception — on purpose

`except:` carves paths out of a rule's scope, so a general rule can have a sanctioned,
reviewable hole:

```yaml
  - henxel: "No secrets in tracked files (the vault is the one allowed home)"
    in: ./*
    except: ["./vault/*"]
    no_secrets: true
```

### Hard-enforce "ask me before staging" in OpenCode

`ask_me_before_staging` is advisory by default (git has no pre-add hook). In OpenCode you
can make it enforced — and the agent installs the guard itself:

```bash
henxels integrate opencode
```

### Budget files in tokens, not just lines

A file too big for the agent's context window is one it can't reason over — so warn in the
unit the agent actually feels:

```yaml
settings:
  warn_about_large_files: { over: 8000 tokens }   # also: 200 lines | 3 kb
```

---

## Documentation

The README is the tour; the deeper guides live in
[`docs/`](https://github.com/benquemax/henxels/tree/main/docs):

- [Getting started](https://github.com/benquemax/henxels/blob/main/docs/getting-started.md) — install, init, validate.
- [Writing henxels](https://github.com/benquemax/henxels/blob/main/docs/writing-henxels.md) — the contract: `in:`, `except:`, `level:`, `why:`.
- [Built-in statements](https://github.com/benquemax/henxels/blob/main/docs/built-in-statements.md) — the standard library.
- [Custom checks](https://github.com/benquemax/henxels/blob/main/docs/custom-checks.md) — write your own statements.
- [Settings](https://github.com/benquemax/henxels/blob/main/docs/settings.md) — behaviours (staging, push, delete, similarity, large files).
- [Guards and bless](https://github.com/benquemax/henxels/blob/main/docs/guards-and-bless.md) — how the protections work.
- [Agent integrations](https://github.com/benquemax/henxels/blob/main/docs/agent-integrations.md) — the AGENTS.md digest and harness hooks.
- [Enforcing OKF](https://github.com/benquemax/henxels/blob/main/docs/enforcing-okf.md) — a worked contract for the Open Knowledge Format.
- [Upgrading](https://github.com/benquemax/henxels/blob/main/docs/upgrading.md) — the version nag, refreshing local files, schema evolution.

---

## Example: an OKF (Open Knowledge Format) contract for your LLM wiki

An **LLM wiki** — a markdown knowledge base an agent reads and writes (the pattern
popularized by Andrej Karpathy) — is a perfect henxels use case. Google's
[Open Knowledge Format (OKF) spec](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
formalizes the pattern: **concept documents** with a `type` in their frontmatter,
cross-links as the edges of a knowledge graph, and reserved `index.md`/`log.md` files.
OKF makes *consumers* tolerate almost anything, so the whole quality bar sits with
whoever writes the bundle — and small models drift hard against that bar: they write
against the conventions, and knowledge that belongs in **one** page ends up **scattered
across several near-duplicate files**. henxels turns the OKF conventions into a contract
the agent has to follow, and warns it the moment it's about to fragment a topic.

One command sets all of this up — seeding a fresh wiki (green at birth), or governing an
existing one gently (rules start at `level: warn`, so the findings are your agent's
migration plan, not blocked commits):

```bash
henxels init --template okf-llm-wiki
```

The heart of the contract it writes:

```yaml
settings:
  confirm_before_deleting: { over_lines: 10 }   # don't lose knowledge to a diff slip
  warn_about_similar_files:                     # the anti-scatter henxel: nudges the
    above: 0.82                                 # agent to UPDATE a page, not clone it
    ignore: ["**/index.md", "**/log.md"]

henxels:
  - henxel: "Every concept doc is kebab-case markdown with OKF frontmatter (type is the one MUST)"
    in: ./wiki/*
    except: ["**/index.md", "**/log.md"]        # OKF's reserved files carry no frontmatter
    allowed_filetypes: .md
    filename_casing: kebab-case
    required_frontmatter: [type, title, description]
    frontmatter_values:
      type: [BigQuery Table, API Endpoint, Metric, Playbook]

  - henxel: "timestamp is a real ISO 8601 datetime and is bumped when a doc changes"
    in: ./wiki/*
    except: ["**/index.md", "**/log.md"]
    frontmatter_dates: { timestamp: datetime }
    bump_updated_on_change: timestamp

  - henxel: "Every link lands — bundle-absolute (/tables/customers.md) and relative alike"
    in: ./wiki/*
    rooted_links_resolve: ./wiki
    links_resolve: true

  - henxel: "OKF reserved files stay frontmatter-free (the bundle root may declare okf_version)"
    in: ["./wiki/**/index.md", "./wiki/**/log.md"]
    except: ./wiki/index.md
    no_frontmatter: true

  - henxel: "The bundle root has an index and every top-level concept is listed in it"
    in: ./wiki
    except: "**/log.md"
    required_files: index.md
    referenced_in: wiki/index.md
```

Because the contract is mirrored into `AGENTS.md`, the agent reads *"one page per
concept, kebab-case, `type` from this list"* **before** it writes — and
`warn_about_similar_files` catches it when it's about to create the fifth
slightly-different page about the same concept. Strong guidance is exactly what small
LLMs need to stay tidy.

The full walk-through —
[Enforcing OKF (Open Knowledge Format)](https://github.com/benquemax/henxels/blob/main/docs/enforcing-okf.md)
— maps every henxel to the spec's conformance rules and adds the graph-connectivity
rule, the `references/` carve-out for citation targets, and a ten-line custom check for
`log.md`'s date sections.

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
| `henxels integrate <harness>` | install an agent-harness integration (e.g. `opencode`) |
| `henxels sync` / `henxels doctor` | refresh the digest / check the setup |

## License

MIT.
