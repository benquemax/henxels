---
title: The brainpick brain starter
summary: The brainpick-brain template — a _brain/ in the brainpick brain format (knowledge, skills, journals, vision, plans, plus raw source material), a first skill that teaches the agent how to use it, and the henxels that keep the data flow honest.
---

# The brainpick brain starter

A **brain** is a wiki meant to be an agent's memory: not a pile of notes but a
governed knowledge graph with a declared data flow, so an agent can *learn* from the
project instead of rediscovering it in every session. The `brainpick-brain` template
scaffolds one in the [brainpick](https://github.com/benquemax/brainpick) brain
format:

```bash
henxels init --template brainpick-brain
brainpick init          # brainpick detects the brain, mints its id, compiles it
```

henxels owns the structure and the contract; brainpick owns compiling and serving it
— to agents via the `brain_*` MCP tools and the CLI, and to humans via a GUI where
you can view and edit it yourself. The format itself (spec/85) and its reasoning live
in [brainpick's wiki](https://github.com/benquemax/brainpick/blob/main/docs/brain.md).

## What it sets up

```text
_brain/
  index.md            OKF root; brainpick regenerates a section of it
  log.md              update log, date-sectioned, newest first
  knowledge/          semantic memory — evergreen concepts
  skills/             procedural memory — actionable, tested procedures
    using-the-brain.md  the first skill: how to read and improve this brain
  journals/           episodic memory — one file per month
    index.md            what a journal is and how the month rolls
    YYYY-MM.md          the current month: a ## YYYY-MM-DD section per day, newest first
    archive/YYYY-MM.md  earlier months, moved here on the first entry of a new month
  raw/                undistilled source material — transcripts, exports, clippings
  vision/             direction — the northstar, written as a book
  plans/              decided work
_todo.md              the parking lot — beside the brain, not in it
_temp/                gitignored scratch (never in the brain)
brainpick.toml        shared policy: [bundle] root + exclude, [index] mode, [brain] format
```

The five folders `knowledge/ skills/ journals/ vision/ plans/` are **memory types**,
one job each, and the contract refuses a sixth: a kind of memory that does not fit
is a `type` value or a sub-folder, never a new sibling. `raw/` beside them is not
memory but the material memory is made from — kept orderly and greppable, and
excluded from the compiled brain (`exclude = ["raw/*"]` in `brainpick.toml`) because
it is noisy by nature. Information flows in one direction — **raw → journals →
knowledge → skills** — and is read in reverse, most distilled first: skills are the
purest, most tested layer, the journals the rawest that still counts as memory.
Reading a less distilled layer is a distillation opportunity.

Journals are logs, not concept docs: no frontmatter, one file per month, every
heading an ISO date. That caps a journal's length forever and keeps history without
it getting in the way. When a new month starts, the agent moves last month's file
into `journals/archive/` before writing the first entry — the first skill says how,
and the contract blocks a commit that forgot (two month files at the top of
`journals/`). It is deliberately not a brainpick command: brainpick reads
frontmatter, never folder layout, so the roll belongs to the agent and the contract.

`_todo.md` and `_temp/` stay beside the brain: project management and scratch are
neither knowledge nor episodes. `brainpick.toml` is committed (shared policy);
`brainpick.local.toml` (model endpoints) and `.brainpick/` (compiled artifacts) are
gitignored by the template.

## The first skill

`skills/using-the-brain.md` is a playbook written for the agent: read the closest
brain first, then `skills/`, then `knowledge/`, then `journals/`, and `raw/` only by
grep to ground or to distil; roll the month; distil upward and
leave a pointer rather than a copy; ground every claim inline; treat the brain as
*the best knowledge available at the moment, not the truth*. Its `description` is a
trigger ("Use when…") and it carries `export: agent-skill`, so brainpick can hand it
to the harness as a loaded skill — the brain's own procedures reach the agent before
it decides anything.

## The henxels behind it

The template appends these rules to the starter contract detected for your project
type (python, node, or generic):

- **The compiled brain is fresh before every commit** — `brainpick compile
  --check-fresh` gates commits; stale artifacts lie to agents.
- **Folders are memory types** — the five memory folders plus `raw/` are required
  and the only ones allowed.
- **Brain material is markdown plus small data and scripts** — `.md`, `.txt`, `.py`,
  `.json`, `.yaml`, `.toml`; scratch goes to `_temp/`.
- **`raw/` is orderly source material, never a dump** — kebab-case names, listed in
  `raw/index.md`, a wider filetype list (`.csv .html .pdf .png .jpg` too), no
  frontmatter or links required.
- **Every concept doc is kebab-case markdown with OKF frontmatter** — `type`,
  `title`, `description`; `timestamp` is a real ISO 8601 datetime bumped on change.
- **Every claim is grounded** — pages in `knowledge/`, `skills/` and `plans/` link out
  at least once (Wikipedia-style, inline); journal entries are the primary sources and
  are exempt.
- **Skills are playbooks that form a dependency tree** — `type: playbook`, edges
  declared in `depends_on`; `skilltree.md` is generated by brainpick, never edited.
- **One journal file per month** — `journals/YYYY-MM.md`, no frontmatter, a
  `## YYYY-MM-DD` section per day, newest first (`filename_matches_regex`,
  `no_frontmatter`, `log_headings_are_dates`); entries point to what they changed
  rather than restating it.
- **Only the current month stays in `journals/`** — `max_files: 1` (the index
  excepted); earlier months live in `journals/archive/`, same shape, untouched.
- **Every link lands** — bundle-absolute and relative alike; reserved `index.md` and
  `log.md` files stay frontmatter-free; update logs are date-sectioned.
- **`vision/` is a book and `plans/` holds decided work** — each with an index every
  page is listed in.
- **`_todo.md` exists, `_temp/` and `brainpick.local.toml` stay gitignored, and no
  credentials anywhere.**

The one custom check (`log_headings_are_dates`) ships in `henxels_checks.py`, as in
the [OKF wiki template](enforcing-okf.md). Every rule carries a `why:` so the agent
reading the digest in `AGENTS.md` sees the reason, not just the rule.

## Several brains

A project brain, a team brain and a personal brain can coexist; brainpick federates
them and links across them by `brain://slug-id/path`. When they conflict, **the
closest brain wins** — the one nearest the implementation — and both are updated.
The template's `[brain] audience` (`personal | team | public`) records who a brain is
written for. Subsidiarity and federation are brainpick's side of the story:
[brain subsidiarity](https://github.com/benquemax/brainpick/blob/main/docs/brain-subsidiarity.md).
