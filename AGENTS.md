# AGENTS.md — henxels

> Suspenders for your repo. Keep your ADHD agent in henxels.

This file is the single source of instructions for agents and contributors working
on **henxels itself**. (`CLAUDE.md` is just `@AGENTS.md`.)

## What this project is

Henxels enforces **file-level constraints** that steer agents and humans to keep a
repository faithful to a contract (`henxels.yaml`). Each rule is a *henxel*. The
contract reads like a document, is mirrored into agents' context, and makes
disobedience impossible *by accident* — overriding a henxel means editing the
contract (a conscious, reviewable act).

See `README.md` for the full vision and the **Principles** section, which steers
every decision here.

## How we work (non-negotiable)

- **TDD.** Write a failing test first, then the minimum code to pass it, then
  refactor. No behavior ships without a test.
- **Tests gate commits.** This repo's own `pre-commit` runs the full test suite
  (`pytest`) **and** `henxels check`. A commit that breaks current behavior or
  regresses anything must not land. Install hooks with `henxels init` (or the
  dev bootstrap below).
- **Do not stage, commit, or push unless asked.** The maintainer stages and pushes
  himself. When work is ready, finish the edits and *ask him to stage/push* — never
  run `git add`/`git commit`/`git push` reflexively.
- **Scratch goes in `_temp/`** (gitignored). Parked ideas go in `_todo.md`. Never
  drop scratch files in the repo root.

## Dev bootstrap

```bash
uv venv && uv pip install -e ".[dev]"
uv run pytest            # run the suite
uv run henxels check     # dogfood the contract on this repo
```

## Code layout

```
henxels/
  cli.py            dispatch: init | check | explain | bless | sync | doctor
  config/           load.py (parse), tree.py (closest-rule resolver)
  engine/           discover.py (walk files), report.py (fancy/plain output)
  rules/            placement, existence, naming, guard, duplication (one henxel each)
  util/             glob.py and small helpers
  schema/           henxels.schema.json (editor autocomplete + enum validation)
  plugins/          markdown, frontmatter (opt-in, demoted optionals)
tests/              mirrors the package; one test module per unit
```

> Note: the rule types live in `henxels/rules/` (not `henxels/henxels/`) to avoid a
> package-name collision; everything else follows the plan.

## Conventions

- Python ≥ 3.10, standard library first; new third-party deps need a reason.
- Output is **plain** when not a TTY or when `NO_COLOR`/`CI` is set; fancy only for
  humans. Never put banners/wordplay into machine-readable output.
- Every henxel violation message carries: what henxel, the `reason`, the `steer`,
  and how to consciously override (edit the contract, or `henxels bless …`).

<!-- henxels:begin -->
## Structure contract (henxels)

_Auto-generated from `henxels.yaml` by `henxels sync`. Do not edit by hand._

Put the right thing in the right place. The **closest rule in the tree wins**.
To disobey a rule, change `henxels.yaml` — that is the only sanctioned escape.
Run `henxels explain <path>` before creating a file to see what governs that spot.

### Where things live

- `henxels/` — files are snake_case, the package — one module per concern
  - `henxels/rules/` — files are snake_case
  - `henxels/config/` — files are snake_case
  - `henxels/engine/` — files are snake_case
  - `henxels/util/` — files are snake_case
  - `henxels/plugins/` — files are snake_case
- `tests/` — files are snake_case, TDD suite — mirrors the package; runs in pre-commit
- `docs/` — files are kebab-case, user documentation — doubles as live test data

### Guards

- **push**: blocked until `henxels bless push`
- **stage**: ask the user first (don't do it reflexively)
- **delete**: deleting files or removing >5 lines is blocked until `henxels bless delete`

### Single source of truth

- project config lives only in `pyproject.toml` — don't create `setup.py`, `setup.cfg`

### Must exist

- `_temp/.gitkeep` — the scratch folder must exist (committed via .gitkeep)
- `_todo.md` — the parking lot should exist locally _(warn)_

### Checks run by the hooks

- **pre_commit**: `uv run pytest -q`
- **pre_push**: `uv run henxels check --all`
<!-- henxels:end -->
