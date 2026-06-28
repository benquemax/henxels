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

## Mental model

A **henxel** is a rule: a sentence + an `in:` scope + one or more **statements** that
must all pass. A **statement** is a named verification function (the reusable unit).
`settings:` holds behaviours (push/delete/stage protections, similarity) — the things
that aren't tests. Logic lives inside statement functions, never in the YAML.

## Code layout

```
henxels/
  cli.py            dispatch: init | check | explain | catalogue |
                    create-new-statement | contribute | bless | sync | doctor
  contract.py       parse settings + henxels list + imports (auto-loads custom checks)
  runner.py         run each henxel's statements (name-injected args) into findings
  statements/       registry (@statement), scope (the injected context), builtins
  settings.py       read behaviours from settings:
  guard.py          push/delete protections (intercept a git action)
  hookrun.py        what pre-commit/pre-push run
  commands.py       run_before_commit/push command gates
  similarity.py     duplication warnings over committed files
  catalogue.py      browse / scaffold / contribute statements
  engine/           discover, gitinfo, report (fancy/plain)
  casing.py         naming conventions; util/glob.py; schema/henxels.schema.json
tests/              one module per unit
```

## Conventions

- Python ≥ 3.10, standard library first; new third-party deps need a reason.
- `ruff` is the arbiter of style (runs in pre-commit + CI). Keep it green.
- A statement returns its **violations as instructions** (empty = pass); the henxel's
  sentence is always shown, so output is actionable for a small model.
- Output is **plain** when not a TTY or when `NO_COLOR`/`CI` is set; fancy only for
  humans. Never put banners/wordplay into machine-readable output.
- Contributions: reusable statements go upstream (see `CONTRIBUTING.md`); ad-hoc ones
  stay in `henxels_checks.py`.
- **`README.md` links must be absolute** (`https://github.com/benquemax/henxels/...`),
  never repo-relative. The README is the long-description on PyPI and npm, where
  relative links are dead. Absolute links work on GitHub too, so use them everywhere in
  the README.

<!-- henxels:begin -->
## The contract (henxels)

_Auto-generated from `henxels.yaml` by `henxels sync`. Do not edit by hand._

Each bullet is a **henxel** (a rule). To disobey one, change `henxels.yaml` —
that is the only sanctioned escape. Run `henxels explain <path>` before creating
a file to see what governs that spot.

> **Git etiquette — important.** Do **not** run `git add`, `git commit`, or `git push` yourself in this repo. When your work is ready, stop and ask the user to review the diff and stage it. Staging on the user's behalf is a mistake here, even if the change looks correct.
>
> _OpenCode agents:_ run `henxels integrate opencode` once to make this **enforced** (it hard-blocks `git add`/`git commit`), not just advisory.

### Rules

- The package code is snake_case (including subpackages) (in ./henxels/*)
- Tests are snake_case and live in tests/ (in ./tests/*)
- Docs are kebab-case markdown, each with a title and summary (in ./docs)
- Project config lives only in pyproject.toml
- Statements stay merge-ready (every one has a help= and a test)
- README links are absolute (it's the long-description on PyPI and npm) (in ./README.md)
- The scratch folder must exist
- The parking lot should exist (gitignored — only a reminder) _(warn)_
- Code is clean and conventional (ruff) before every commit
- The test suite passes before every commit
- The contract holds before every push

### Behaviours

- **never `git add` / `git commit` / `git push` yourself** — ask the user to review and stage
- push is blocked until `henxels bless push`
- deleting files / removing many lines is blocked until `henxels bless delete`
- warns when a new file looks like a near-copy of a committed one

### Custom henxels & contributing

**Before writing a custom check, run `henxels catalogue` and use the built-in that
matches your intent — don't reinvent one.** Never name a custom check after a built-in
or a setting (e.g. `warn_about_large_files` is a setting, not a check).

Need a check that genuinely doesn't exist? `henxels create-new-statement <name>` scaffolds a local check
(auto-loaded from `henxels_checks.py`). **If your check is reusable** — useful in
other repos, not tied to this one — contribute it upstream with `henxels contribute`.
We're in the agentic era: send a ready-to-merge PR instead of opening an issue.
<!-- henxels:end -->
