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

**File-level constraints that steer agents and humans to keep a repository true to a
contract.** Each rule is a *henxel* (from Finnish _henkselit_, "suspenders" — the
external straps that hold everything together and give it shape).

henxels is for repos where small, eager, easily-distracted coding agents keep writing
the right thing in the wrong place — a test beside the source, a second `utils.py`, a
duplicated config that quietly diverges. It puts the expected structure **in front of
the agent** (in `AGENTS.md` and on demand), and makes breaking it **impossible to do
by accident**. To disobey a henxel you have to change the contract — which makes every
deviation a conscious, reviewable decision.

> Basic henxels keep most agents in line. The wilder the agent, the more henxels you
> add. The contract grows with how much restraint your agent needs.

---

## Principles

These steer everything henxels does.

1. **The contract is the single source of structural truth.** If it isn't in
   `henxels.yaml`, it isn't a rule. No structure logic hides in code.
2. **Read it like a document.** A human — or a small model — understands the repo's
   shape by reading the contract, without reading a single validator.
3. **Steer before you stop.** Every henxel says _why_ it exists and _where to put the
   thing instead_. The first job is placement; failing is the fallback.
4. **Disobey responsibly.** Violations aren't forbidden — they're made impossible _by
   accident_. The only escape hatch is editing the contract, so deviations are
   deliberate and visible in the diff.
5. **Closest rule wins.** The nearest henxel in the tree governs; rules cascade into
   subfolders.
6. **Awareness beats blocking.** Especially for duplication — warn, point at the
   canonical home, and trust the conscious act.
7. **Beautiful for humans, silent for machines.** Fancy in a terminal; plain in a pipe.
   Never noisy where it matters.

---

## Quick start

### Give this to your coding agent

Paste this prompt to your agent (Claude Code, opencode, Cursor, …) and let it do the
work:

> **Install henxels in this project and set it up.**
> henxels is a Python tool with a node launcher. Do whatever this project's stack
> makes easy: `uvx henxels` (no install), or `pipx install henxels`, or
> `python -m pip install henxels`, or `npm i -D henxels` (it shims to Python).
> If a prerequisite (Python, uv, pipx, or npm) is missing, install it first.
> Then run `henxels init` in the repo root and report what it created.
> After that, read `henxels.yaml`, tailor the `tree:` to this repo's actual folders,
> and run `henxels sync` followed by `henxels check --all`.

### Or do it yourself

```bash
uvx henxels init        # zero-install via uv  (or: pipx install henxels)
# …edit henxels.yaml to match your repo…
henxels sync            # refresh the AGENTS.md digest
henxels check --all     # validate everything
```

`henxels init` will:

- detect your stack (python / node / generic) and scaffold a commented `henxels.yaml`,
- install teaching git hooks (`pre-commit`, `pre-push`),
- write a contract digest into `AGENTS.md` (in a managed block),
- print exactly what to tweak next.

---

## The contract

`henxels.yaml` reads top to bottom like a document. Readable keys, precise values, and
every rule carries a plain-language `reason` / `steer` for humans and agents alike.

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/benquemax/henxels/main/henxels/schema/henxels.schema.json
henxels: 1

guards:                 # make destructive reflexes a conscious act
  push: bless
  delete:
    mode: bless
    line_threshold: 5
  stage: ask

similarity:             # duplication awareness over committed files (warn only)
  warn_above: 0.85
  exclude: ["**/__init__.py"]

canonical:              # the one true home of a thing
  - role: "project config"
    file: pyproject.toml
    forbid_lookalikes: ["setup.py", "setup.cfg"]

tree:                   # closest rule wins; rules cascade into subfolders
  src:
    naming: snake_case
    forbid:
      - glob: "**/*_test.py"
        reason: "tests live in tests/, not beside the source"
        steer: "create the test under tests/ mirroring this path"
  tests:
    naming: snake_case
  docs:
    naming: kebab-case
```

### Henxel types

| Henxel | What it does | Severity |
|--------|--------------|----------|
| `forbid` | a kind of file may not live in this folder subtree | block |
| `require` | this folder must contain a named file | block |
| `naming` | files here follow a convention (`snake_case`, `kebab-case`, `camelCase`, `PascalCase`, `SCREAMING_SNAKE_CASE`, `any`) | block |
| `canonical` | a role lives in one file; look-alikes are forbidden | block |
| `similarity` | a new file looks like a near-copy of a committed one | warn |
| `guards` | `push` / `delete` / `stage` require a conscious act | block / ask |

The sanctioned way to override any **block** is to edit `henxels.yaml`.

---

## Guards & bless

Guards stop reflexive, hard-to-undo actions. They don't forbid — they make you mean it.

```text
$ git push
✗ guard:push: push is guarded — a push is hard to take back
    why: reflexive pushes leak half-done work and rewrite shared history
    → when you really mean it, bless the push
    bless: henxels bless push   (then push again)
```

`henxels bless push` mints a **one-time** token bound to the exact commit being pushed;
the hook consumes it. A reflexive retry can't slip through, and the bless expires fast.

The **delete guard** covers deleted files _and_ net-removed lines (over
`line_threshold`) — because small agents lose rows through diff-edit mistakes, not just
`rm`. `henxels bless delete` confirms exactly the staged deletions.

`stage: ask` is a steer, not a block (git has no pre-add hook): henxels reminds the
agent — via the `AGENTS.md` digest — to let _you_ stage and push.

---

## For agents (AX)

- **`henxels explain <path>`** — before creating or moving a file, ask what governs that
  spot and where the thing actually goes. This is the steering keystone.
- **`AGENTS.md` digest** — `henxels sync` keeps a managed block in `AGENTS.md` with the
  whole contract in plain language. Human text outside the block is never touched.
- **`henxels check --staged`** — runs in the pre-commit hook; teaches on every block.

---

## Editor support

The bundled JSON Schema gives you autocomplete and enum validation in `henxels.yaml`.
The scaffold drops a modeline so editors with the YAML language server pick it up:

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/benquemax/henxels/main/henxels/schema/henxels.schema.json
```

---

## CI

```yaml
# .github/workflows/henxels.yml
name: henxels
on: [push, pull_request]
jobs:
  contract:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pipx install henxels
      - run: henxels check --all
```

Exit codes: `0` clean · `1` a henxel snapped · `2` usage/contract problem.

---

## Commands

| Command | Purpose |
|---------|---------|
| `henxels init` | scaffold contract + hooks + digest |
| `henxels check [--all\|--staged] [paths…]` | validate against the contract |
| `henxels explain <path>` | what governs this location, in plain words |
| `henxels bless <push\|delete>` | consciously override a guard, once |
| `henxels sync` | refresh the `AGENTS.md` digest |
| `henxels doctor` | verify the setup is wired correctly |

---

## How it's built

henxels is built test-first; its own pre-commit runs the full suite plus
`henxels check`, so nothing ships that breaks or regresses. See `AGENTS.md`.

## License

MIT.
