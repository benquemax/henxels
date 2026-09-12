---
title: The brainpick brain starter
summary: The brainpick-brain template — a _brain/ in brainpick brain format 2 (knowledge, skills, journals by day, todo, vision, plans, conventions, plus raw source material), a slow half-life, a first skill that teaches the agent how to use it, and the henxels that keep the data flow honest.
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
  journals/           episodic memory — one file per day
    index.md            what a journal is and how the day rolls
    YYYY-MM-DD.md       today: entries newest first under any heading (## HH:MM or a title)
    archive/YYYY/MM/    every earlier day, moved here before the first entry of a new day
  todo/               the brain's own work queue — in the brain, so it is searchable
    index.md            what lives here
    open.md             the live list: a `type: todo` doc of `- [ ]` / `- [x]` lines
    archive/YYYY-MM-DD.md  what was closed that day, one file per day
  raw/                undistilled source material — transcripts, exports, clippings
  vision/             direction — the northstar, written as a book
  plans/              decided work
  conventions/        decided rules and principles — how things get done, standing
_temp/                gitignored scratch (never in the brain)
brainpick.toml        shared policy: [bundle] root + exclude, [index] mode, [brain] format = 2, [half_life]
```

The six folders `knowledge/ skills/ journals/ vision/ plans/ conventions/` are
**memory types**, one job each, and the contract refuses a seventh: a kind of
memory that does not fit is a `type` value or a sub-folder, never a new sibling.
Two siblings are not memory types. `todo/` is the brain's own work queue — kept
*in* the brain, unlike a gitignored parking lot, so brainpick compiles its
checklist lines into `todos.json`, counts the open ones in `brain_overview` and
finds them in search. `raw/` is the material memory is made from — kept orderly
and greppable, and excluded from the compiled brain (`exclude = ["raw/*"]` in
`brainpick.toml`) because it is noisy by nature.
Information flows in one direction — **raw → journals → knowledge → skills**,
with a settled decision breaking off into `conventions/` (`type: decision`)
instead when it applies broadly rather than to one task — and is read in
reverse, most distilled first: skills are the purest, most tested layer, the
journals the rawest that still counts as memory. Reading a less distilled
layer is a distillation opportunity.

Journals are logs, not concept docs: no frontmatter, one file per day, the date in
the file name so headings inside are free. That caps a journal's length forever,
keeps history without it getting in the way, and gives the half-life a file-level
unit. Before the first entry of a new day, the agent moves yesterday's file into
`journals/archive/YYYY/MM/` — the first skill says how, and the contract blocks a
commit that forgot (two day files at the top of `journals/`). It is deliberately not
a brainpick command: brainpick reads frontmatter, never folder layout, so the roll
belongs to the agent and the contract. A grounding link to a day is a link to its
file, no anchor: `../journals/archive/2026/09/2026-09-07.md`.

To-dos follow the same rhythm. A task that surfaces mid-work lands in `todo/open.md`
as `- [ ] …`; when it is done it is ticked `- [x] … (done: YYYY-MM-DD)` and the line
moves to `todo/archive/YYYY-MM-DD.md` — the same day or the next, the contract
insists — so `open.md` stays small and "done" is an episode with a date. The
archive holds only done items; the engine never edits a list.

**Memories fade — slowly.** `brainpick.toml` ships a `[half_life]` block: a doc's
search score is multiplied by `2^(-age / half_life)` on its `timestamp`, floored so
nothing ever disappears, only ranks lower. The default is deliberately slow (365
days; `journals` 180, `todo` 90, `skills` 0 — procedural memory never fades). The
knob is for agents: when the lists silt up with stale material, **steepen the
curve** — fewer days for a folder, or a per-page `half_life:` in frontmatter —
rather than deleting. Nothing is hidden by it; it is a ranking, not a purge.

`_temp/` stays beside the brain: scratch is neither knowledge nor an episode.
`brainpick.toml` is committed (shared policy); `brainpick.local.toml` (model
endpoints) and `.brainpick/` (compiled artifacts) are gitignored by the template.

### Coming from format 1

A brain scaffolded before 0.17 has month journals (`journals/YYYY-MM.md` with
`## YYYY-MM-DD` sections), a gitignored `_todo.md` and `format = 1`. Brainpick
does the content move; the contract is the agent's:

1. `brainpick migrate --to 2` (add `--dry-run` first to see the action list
   and a diff). It splits every month file into day files — today's into
   `journals/`, every other day into `journals/archive/YYYY/MM/` — rewrites
   every link to a month or a day section onto the day file, moves `_todo.md`
   into `todo/open.md` (`type: todo`), drops it from `.gitignore`, seeds
   `todo/index.md` and sets `format = 2`. A brain still on format 1 hears
   about this command at every `brainpick compile` (its what's-new notice).
2. Add the `[half_life]` block to `brainpick.toml` (copy it from a fresh
   `henxels init --template brainpick-brain --dry-run` elsewhere, or from this
   page), replace the journal and `_todo.md` henxels in `henxels.yaml` with the
   fragment `henxels init` prints when a contract already exists, and add the
   new custom checks to `henxels_checks.py`.
3. Review with `git diff`, `henxels check --all`, then `brainpick compile`.

## The first skill

`skills/using-the-brain.md` is a skill (`type: skill` — a `playbook` is a how-to for
humans and brainpick does not list it as a skill) written for the agent: **pull the brain's
latest version before reading anything** (it is shared memory — others commit to it
between sessions, and a stale checkout is knowledge the brain has already
corrected); then read the closest brain first, then `skills/`, then `conventions/`, then
`knowledge/`, then `journals/`, then `todo/open.md`, and `raw/` only by grep to ground or to distil; roll the day;
tick and archive to-dos; distil a procedure that works into a skill (`brainpick skill new`);
steepen the half-life when the lists silt up; distil upward, commit and push what you changed, and
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
- **Folders are memory types** — the six memory folders plus `todo/` and `raw/` are
  required and the only ones allowed.
- **Brain material is markdown plus small data and scripts** — `.md`, `.txt`, `.py`,
  `.json`, `.yaml`, `.toml`; scratch goes to `_temp/`.
- **`raw/` is orderly source material, never a dump** — kebab-case names, listed in
  `raw/index.md`, a wider filetype list (`.csv .html .pdf .png .jpg` too), no
  frontmatter or links required.
- **Every concept doc is kebab-case markdown with OKF frontmatter** — `type`,
  `title`, `description`; `timestamp` is a real ISO 8601 datetime bumped on change.
- **Every claim is grounded** — pages in `knowledge/`, `skills/`, `plans/` and
  `conventions/` link out at least once (Wikipedia-style, inline); journal entries
  are the primary sources and are exempt.
- **Skills are `type: skill` and form a dependency tree** — edges declared in
  `depends_on`, every path under `tools:` exists (`skill_tools_exist`; the scripts
  live in `skills/tools/`, exempt from the concept-doc rules); `skilltree.md` is
  generated by brainpick, never edited.
- **One journal file per day** — `journals/YYYY-MM-DD.md`, no frontmatter, headings
  free (`filename_matches_regex`, `no_frontmatter`); entries point to what they
  changed rather than restating it.
- **Only today stays in `journals/`** — `max_files: 1` (the index excepted); earlier
  days live in `journals/archive/YYYY/MM/`, the folders matching the file name
  (`archived_journals_sit_under_year_month`), untouched.
- **`todo/` is the work queue** — `index.md` and `open.md` required, every doc
  `type: todo`; a ticked item in `open.md` carries `(done: YYYY-MM-DD)` and leaves
  for `archive/YYYY-MM-DD.md` the next day, and the archive holds only done items
  (`done_todos_are_archived`).
- **Every link lands** — bundle-absolute and relative alike; reserved `index.md` and
  `log.md` files stay frontmatter-free; update logs are date-sectioned.
- **`vision/` is a book, `plans/` holds decided work, `conventions/` holds decided
  rules** — each with an index every page is listed in; `conventions/` pages are
  also restricted to `type: decision`.
- **`_temp/` and `brainpick.local.toml` stay gitignored, and no credentials
  anywhere.**

The custom checks (`log_headings_are_dates` — the same one the
[OKF wiki template](enforcing-okf.md) ships — plus `skill_tools_exist`,
`archived_journals_sit_under_year_month` and `done_todos_are_archived`) ship in
`henxels_checks.py`. Every rule carries a `why:` so the agent reading the digest in
`AGENTS.md` sees the reason, not just the rule.

## Several brains

A project brain, a team brain and a personal brain can coexist; brainpick federates
them and links across them by `brain://slug-id/path`. When they conflict, **the
closest brain wins** — the one nearest the implementation — and both are updated.
The template's `[brain] audience` (`personal | team | public`) records who a brain is
written for. Subsidiarity and federation are brainpick's side of the story:
[brain subsidiarity](https://github.com/benquemax/brainpick/blob/main/docs/brain-subsidiarity.md).
