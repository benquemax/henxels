---
title: The agentic project starter
summary: The agentic-project template — a parking lot (_todo.md), gitignored scratch space (_temp/), a vision book (_vision/), and a plans shelf (_plans/), with the henxels that keep them honest.
---

# The agentic project starter

Agent-driven projects accumulate loose ends fast: half-decided ideas, scratch files,
plans that live only in a chat scrollback. The `agentic-project` template gives all of
that a home — and a contract that keeps each home honest:

```bash
henxels init --template agentic-project
```

## What it sets up

- **`_todo.md`** — the parking lot. Tasks that surface mid-work but fall outside its
  scope go here instead of derailing the task at hand.
- **`_temp/`** — free scratch space, gitignored. Anything temporary goes here; nothing
  in it is ever committed.
- **`_vision/`** — the northstar, written as a book. `index.md` is the table of
  contents; a chapter not linked from it is invisible and effectively not part of the
  vision.
- **`_plans/`** — written plans for work that has been *decided*. Undecided ideas
  belong in `_todo.md` or `_vision/`, not here.

## The henxels behind it

The template appends these rules to the starter contract detected for your project
type (python, node, or generic):

- **No credentials anywhere in the repo** — `no_secrets` over the whole tree,
  subfolders included.
- **`_todo.md` exists at the repo root.**
- **`_temp` stays gitignored** — checked with `git check-ignore` before every commit.
- **`_vision` is a book** — kebab-case markdown chapters, every page linked from
  `_vision/index.md`.
- **`_plans` holds kebab-case markdown plans** — with an `index.md` of its own.

Like every template, it is green at birth: the seeds satisfy the rules from the first
`henxels check`, seeding is additive only (existing files are never overwritten), and
an existing `henxels.yaml` is left untouched — init prints the fragment for you to
paste instead. To bend any rule, edit `henxels.yaml`; that is the whole idea.
