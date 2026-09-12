"""The brainpick brain starter (``henxels init --template brainpick-brain``).

A brain is a wiki meant to be an agent's memory: ``_brain/`` with six memory-type
folders (knowledge, skills, journals, vision, plans, conventions), the brain's own
work queue (todo/), raw source material, a declared data flow (journals →
knowledge → skills, read in reverse; a settled decision → a conventions page
alongside it), inline grounding, and a first skill that teaches the agent how to
use and improve it. brainpick's spec/85 fixes the format — this is **brain format
2**: a journal file per day rolled into ``archive/YYYY/MM/``, to-do lists inside
the brain as ``type: todo`` checklists, a slow half-life agents may steepen. This
template scaffolds it — structure + contract live here, serving (``brainpick
init``, compile, the ``brain_*`` MCP tools) is brainpick's half of the handoff:
https://github.com/benquemax/brainpick
"""

from __future__ import annotations

import datetime
from pathlib import Path
from string import Template

BRAIN_DIR = "_brain"
BRAIN_FOLDERS = ("knowledge", "skills", "journals", "todo", "vision", "plans", "conventions", "raw")
BRAIN_FORMAT = 2  # brainpick spec/85; bumped only with a migration path
HALF_LIFE_DEFAULT_DAYS = 365  # slow by default — steepen on purpose when lists silt up
BRAINPICK_URL = "https://github.com/benquemax/brainpick"

BRAIN_SETTINGS = """
# Behaviours (not tests): protections + tuning knobs.
settings:
  ask_me_before_staging: true     # don't `git add` for me — ask instead
  confirm_before_push: true       # block `git push` until `henxels bless push`
  confirm_before_deleting:        # deletion is deliberate
    over_lines: 10
  warn_about_similar_files:       # one concept, ONE document — update it,
    above: 0.82                   # don't clone a near-duplicate
    ignore: ["**/__init__.py", "**/index.md", "**/log.md", "**/skilltree.md"]
"""

_BRAIN = Template("""
  # --- the brainpick brain (brainpick-brain template) ----------------------
  # $brain/ is a BRAIN: an OKF wiki that is this project's agent memory, in the
  # brainpick brain format (spec/85). Folders are memory types; information
  # flows journals -> knowledge -> skills and is read in reverse. The why:
  # $url/blob/main/docs/brain.md
  - henxel: "One brain, one bundle root — and it is compiled fresh before every commit"
    why: >
      Agents navigate the COMPILED brain (brainpick's index, link graph,
      vectors), not the raw files. Stale artifacts lie to agents, so the
      freshness gate runs before every commit. Serve it with `brainpick init`.
    in: .
    required_files: brainpick.toml
    run_before_commit: brainpick compile --check-fresh

  - henxel: "Folders are memory types — knowledge, skills, journals, vision, plans, conventions — one job each; todo/ is the work queue, raw/ is source material"
    why: >
      knowledge/ is semantic memory (evergreen concepts), skills/ procedural
      (distilled, actionable procedures), journals/ episodic (one file per
      day, rolled into archive/YYYY/MM/), vision/ direction (a book), plans/
      decided work, conventions/ decided rules and principles for HOW things
      get done (standing policy — naming, process, contracts — not a
      specific task like plans/, not a step-by-step procedure like skills/).
      todo/ is not a memory type: it is the brain's own work queue — open.md
      the live checklist, archive/YYYY-MM-DD.md what was closed that day —
      kept in the brain so it is searchable and counted. raw/ is not one
      either: undistilled source material (transcripts, exports, clippings)
      that knowledge grounds on — governed for order, exempt from OKF, and
      excluded from brainpick's results. Nothing is replicated across
      layers. A memory type that does not fit is a `type` value or a
      sub-folder, never a new sibling. Read skills/ first — it is the most
      distilled, tested and pure layer — then conventions/, then
      knowledge/, then journals/; grep raw/ only to ground or to distil.
      Data flow architecture: $url/blob/main/docs/data-flow-architecture.md
    in: ./$brain
    required_files: index.md
    required_subfolders: [knowledge, skills, journals, todo, vision, plans, conventions, raw]
    only_these_subfolders: [knowledge, skills, journals, todo, vision, plans, conventions, raw]

  - henxel: "Brain material is markdown plus small data and scripts; scratch is _temp/"
    why: >
      Catalogues and tooling may live in the brain, but only these types count
      as brain material. brainpick indexes the markdown; the rest is allowed
      but invisible to the graph. Anything temporary goes to _temp/; raw/
      has its own, wider list below.
    in: ./$brain/*
    except: $brain/raw/*
    allowed_filetypes: [.md, .txt, .py, .json, .yaml, .toml]

  - henxel: "raw/ is orderly source material — kebab-case, indexed, greppable — never a dump"
    why: >
      Raw data is undistilled but valuable: it is what knowledge grounds on
      and what future distillation reads. It needs no frontmatter and no
      links, but it is kept clean: kebab-case names that say what a file
      is, listed in raw/index.md, and pruned when it has been distilled or
      proved worthless. brainpick excludes raw/ from search results (see
      brainpick.toml) so it never drowns the distilled layers; grep it.
    in: ./$brain/raw/*
    except: $brain/raw/index.md
    filename_casing: kebab-case
    allowed_filetypes: [.md, .txt, .csv, .json, .yaml, .toml, .html, .pdf, .png, .jpg]

  - henxel: "Every concept doc is kebab-case markdown with OKF frontmatter (type is the one MUST)"
    why: >
      type, title and description keep a page findable and compilable; a
      description containing `: ` must be quoted. Follows the Open Knowledge
      Format: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
    in: ./$brain/*
    except: ["**/index.md", "**/log.md", "**/skilltree.md", "$brain/journals/**", "$brain/raw/**", "$brain/skills/tools/**"]
    allowed_filetypes: .md
    filename_casing: kebab-case
    required_frontmatter: [type, title, description]

  - henxel: "Freshness is explicit — timestamp is a real ISO 8601 datetime bumped whenever a doc changes"
    in: ./$brain/*
    except: ["**/index.md", "**/log.md", "**/skilltree.md", "$brain/journals/**", "$brain/raw/**", "$brain/skills/tools/**"]
    frontmatter_dates: { timestamp: datetime }
    bump_updated_on_change: timestamp

  - henxel: "Every claim is grounded — knowledge, skills, plans and conventions link to where they came from"
    why: >
      Wikipedia-style, inline, a plain link at the claim: a journal entry (a
      decision this brain made), an external page, another brain
      (brain://slug-id/path), or say in words that it is an assumption. A
      page with no outbound links is ungrounded and fails, not warns.
      Journals are the primary sources and are exempt.
      $url/blob/main/docs/grounding.md
    in: ["./$brain/knowledge/*", "./$brain/skills/*", "./$brain/plans/*", "./$brain/conventions/*"]
    except: ["**/index.md", "**/skilltree.md"]
    min_outbound_links: 1

  - henxel: "Skills are type: skill and form a dependency tree — declare depends_on, list tools that exist, never edit skilltree.md"
    why: >
      A skill is a procedure an AGENT follows: `type: skill`, the one value
      brainpick recognises, lists first and boosts in search (a `playbook`
      is a how-to for humans and is not a skill). It lists the skills it
      assumes in `depends_on` frontmatter (bundle-relative .md paths; omit
      it or use `[]` when it assumes nothing) and the deterministic scripts
      it drives in `tools` (bundle-relative paths that must exist — brainpick
      indexes and points at them, never runs them). skilltree.md is
      generated from those edges by brainpick — edit the skills, never the
      tree. A skill with `export: agent-skill` is also written out as a
      harness-loaded SKILL.md pointer by `brainpick integrate`, so the
      brain's procedures reach the agent before it decides anything. Start
      one with `brainpick skill new <name>`.
    in: ./$brain/skills/*
    except: ["**/index.md", "**/skilltree.md", "$brain/skills/tools/**"]
    frontmatter_values:
      type: [skill]
    skill_tools_exist: ./$brain    # custom check, lives in henxels_checks.py

  - henxel: "One journal file per day — journals/YYYY-MM-DD.md — entries newest first under any heading"
    why: >
      Journals are episodic memory: what happened, when. A day per file
      caps the length forever and gives brainpick's half-life a file-level
      unit; the date is the file name, so headings inside are free (`##
      HH:MM` or a title). An entry links forward to the knowledge or skill
      it changed instead of restating it (DRY by pointer, in the direction
      of distillation); when you distil an entry, add the pointer to it.
      Journals are logs, not concept docs: no frontmatter.
    in: ./$brain/journals
    except: ./$brain/journals/index.md
    allowed_filetypes: .md
    filename_matches_regex: '^\\d{4}-\\d{2}-\\d{2}\\.md$$'
    no_frontmatter: true

  - henxel: "Only today stays in journals/ — every earlier day moves to journals/archive/YYYY/MM/"
    why: >
      History without the bulk: before the first entry of a new day, move
      yesterday's file to journals/archive/YYYY/MM/ (same name; mkdir -p it
      the first time). Two unarchived days block the commit, so the roll
      cannot be forgotten. Archived days are read-only history; brainpick
      indexes both, and a grounding link to a day is a link to its file, no
      anchor: ../journals/archive/2026/09/2026-09-07.md.
    in: ./$brain/journals
    except: ./$brain/journals/index.md
    only_these_subfolders: [archive]
    max_files: 1

  - henxel: "Archived journals sit under archive/YYYY/MM/, one day per file, untouched otherwise"
    in: ./$brain/journals/archive/*
    allowed_filetypes: .md
    filename_matches_regex: '^\\d{4}-\\d{2}-\\d{2}\\.md$$'
    no_frontmatter: true
    archived_journals_sit_under_year_month: ./$brain/journals/archive    # custom check, lives in henxels_checks.py

  - henxel: "Every link lands — bundle-absolute (/a/b.md) and relative alike"
    in: ./$brain/*
    rooted_links_resolve: ./$brain
    links_resolve: true

  - henxel: "OKF reserved files stay frontmatter-free; the root index is compile-managed"
    why: >
      $brain/index.md is regenerated by `brainpick compile` ([index] mode =
      "section") — edit the docs' descriptions, never the generated block.
    in: ["./$brain/**/index.md", "./$brain/**/log.md"]
    except: ./$brain/index.md
    no_frontmatter: true

  - henxel: "Update logs are date-sectioned, newest first"
    in: ./$brain/**/log.md
    log_headings_are_dates: true    # custom check, lives in henxels_checks.py

  - henxel: "vision/ is a book — index.md is the table of contents; an unlinked chapter is invisible"
    in: ./$brain/vision
    required_files: index.md
    referenced_in: ./$brain/vision/index.md
    except: ./$brain/vision/index.md

  - henxel: "plans/ holds DECIDED work only, every plan listed in its index"
    why: >
      Undecided ideas belong in todo/open.md (a task) or journals/ (an
      insight), not here.
    in: ./$brain/plans
    required_files: index.md
    referenced_in: ./$brain/plans/index.md
    except: ./$brain/plans/index.md

  - henxel: "conventions/ holds decided rules and principles, one per page, every one listed in its index"
    why: >
      A convention is a standing answer to "how do we do this" — naming,
      process, a contract a team holds itself to — decided once and applied
      broadly, unlike plans/ (one specific piece of work) or skills/ (a
      procedure to execute). type: decision keeps it distinct from
      knowledge/'s general concepts; ground each one the same way any other
      claim is grounded (the decision episode, an external source, or a
      stated assumption).
    in: ./$brain/conventions
    required_files: index.md
    referenced_in: ./$brain/conventions/index.md
    except: ./$brain/conventions/index.md
    frontmatter_values:
      type: [decision]

  - henxel: "todo/ is the brain's work queue — open.md the live type: todo checklist, done items archived by day"
    why: >
      Open work is part of the brain, so it is searchable and counted:
      brainpick compiles every `- [ ]` / `- [x]` line of a `type: todo` doc
      into todos.json, the overview says how many are open, and a search
      hit on a list carries its counts. Tasks that surface mid-work go to
      todo/open.md instead of derailing the task at hand; check it before
      planning any new work — it may already flag a known imperfection or
      something overlapping the task. A ticked item ends in `(done:
      YYYY-MM-DD)` and moves to todo/archive/YYYY-MM-DD.md — the day it was
      closed — the next day at the latest, so open.md stays small and
      "done" is an episode with a date. The archive holds only done items.
    in: ./$brain/todo/*
    except: ./$brain/todo/index.md
    required_files: [index.md, open.md]
    only_these_subfolders: [archive]
    frontmatter_values:
      type: [todo]
    done_todos_are_archived: ./$brain/todo    # custom check, lives in henxels_checks.py

  - henxel: "_temp stays gitignored"
    why: >
      _temp/ is free scratch space; nothing in it is ever committed, and
      brainpick always excludes it from the brain.
    in: .
    run_before_commit: git check-ignore -q _temp

  - henxel: "Shared policy committed, machine-local config never — and no credentials anywhere"
    why: >
      brainpick.toml (index mode, [brain] audience, the bundle id) is shared
      and versioned. brainpick.local.toml (model endpoints, tokens) is
      gitignored. No secret ever enters the repo.
    no_secrets: true    # no `in:` = the whole repo — subfolders included

  - henxel: "brainpick.local.toml is never committed"
    in: .
    run_before_commit: git check-ignore -q brainpick.local.toml
""")

_SEED_INDEX = """---
okf_version: "0.1"
---

# Brain

This is a brain: the agent memory of this project, in the brainpick brain
format. Start with [Using the brain](skills/using-the-brain.md). The section
below is generated by `brainpick compile` — edit the docs, not the block.
"""

_SEED_LOG = """# Brain update log

## {today}

* **Creation**: Brain initialized with the brainpick-brain henxels template.
"""

_SEED_JOURNALS_INDEX = """# Journals

Episodic memory — what happened, when. One file per day (`YYYY-MM-DD.md`),
entries newest first under any heading (`## HH:MM` or a title). Only today
lives here; before the first entry of a new day, move yesterday's file into
`archive/YYYY/MM/` (`mkdir -p` it the first time). Entries point to the
knowledge or skill they changed instead of restating it. A link to a day is
a link to its file: `archive/2026/09/2026-09-07.md`.
"""

_SEED_RAW_INDEX = """# Raw

Undistilled source material: transcripts, exports, clippings, data dumps —
what knowledge pages ground on and what future distillation reads. No
frontmatter, no links required, but orderly: kebab-case names that say what
a file is, listed here, pruned once distilled or proved worthless. brainpick
excludes this folder from search results; grep it.

## Files

(none yet)
"""

_SEED_JOURNAL_DAY = """# {today}

## Brain created

* First skill: [Using the brain](../skills/using-the-brain.md).
"""

_SEED_TODO_INDEX = """# Todo

The brain's own work queue: `open.md` is the live list, `archive/` holds what
was closed, one file per day (`YYYY-MM-DD.md`).

- [Open](open.md)
"""

_SEED_TODO_OPEN = """---
type: todo
title: Open
description: What is still to be done — the brain's live work queue.
timestamp: {today}T00:00:00Z
---

# Open

Tasks that surface mid-work land here instead of derailing the task at hand.
Check this list before planning new work. Tick an item as `- [x] … (done:
YYYY-MM-DD)` and move it to `archive/YYYY-MM-DD.md` the same or the next day.

- [ ] Write the first knowledge page and ground it in today's journal
"""

_SEED_KNOWLEDGE_INDEX = """# Knowledge

Semantic memory — evergreen concept docs, one concept per kebab-case page.
Ground every claim inline (a journal entry, a link, or say it is assumed).
When a concept becomes a procedure that works, distil it into `../skills/`
and point here to the skill.
"""

_SEED_VISION_INDEX = """# Vision

The northstar this project aims towards, written as a book. Every chapter is
listed here — an unlisted chapter is not part of the vision.

## Chapters

* (none yet)
"""

_SEED_PLANS_INDEX = """# Plans

Written plans for work that has been decided — one kebab-case page per plan,
each listed here. Undecided ideas belong in `../todo/open.md` or the journal.

## Plans

* (none yet)
"""

_SEED_CONVENTIONS_INDEX = """# Conventions

Decided rules and principles for HOW things get done — naming, process,
contracts a team holds itself to. One kebab-case page per convention,
`type: decision`, listed here. Not a specific piece of work (that is
`plans/`) and not a step-by-step procedure (that is `skills/`) — a standing
answer to a "how do we do this" question, applied broadly.

## Conventions

* (none yet)
"""

_SEED_SKILL = """---
type: skill
title: Using the brain
description: Use when reading from or writing to this project's brain — before answering from memory, before grepping, and before adding or changing any doc in _brain/.
timestamp: {today}T00:00:00Z
depends_on: []
export: agent-skill
---

# Using the brain

`_brain/` is this project's memory. It is the **best knowledge available at
the moment, not the truth**: everything in it is provisional, and your job
when you notice a flaw is to fix the brain, not route around it.

## First: pull

**Before reading anything, pull the brain's latest version** (`git pull`
in the repo that holds it — every brain, if several are mounted). A brain
is shared memory: other agents and people commit to it between your
sessions, and an answer built on a stale checkout is built on knowledge
the brain has already corrected. Pull first, then read; if the pull brings
changes, re-read before acting on what you remembered.

## Reading: most distilled first

1. **The closest brain first.** If several brains are available (this
   project's, a team's, your personal one), the one closest to the
   implementation wins when they disagree.
2. **`skills/`** — actionable, tested procedures. The purest layer.
3. **`conventions/`** — decided rules and principles for how things get
   done, standing across many tasks. Check these before planning new work:
   a convention can rule out an approach outright.
4. **`knowledge/`** — evergreen concepts, for the idea behind a skill or a
   fact no skill covers yet.
5. **`journals/`** — dated episodes, only when nothing distilled exists.
   Today is `journals/YYYY-MM-DD.md`; earlier days are in
   `journals/archive/YYYY/MM/`.
6. **`todo/open.md`** — the brain's open work. Check it before planning:
   it may already flag what you are about to rediscover.
7. **`raw/`** — undistilled source material. Not in search results; grep it
   to ground a claim or to distil something new.

With brainpick: `brain_overview` first, then `brain_search`, then
`brain_read`. Grep only after the brain comes up short.

## Writing: distil upward, point, ground

- **Information flows `journals/` → `knowledge/` → `skills/`.** An episode
  becomes a concept when it settles; a concept becomes a skill when it has
  been carried out and works. A decision that settles into a standing rule
  — applied broadly, not just this one time — becomes a `conventions/` page
  instead, `type: decision`, alongside that flow rather than inside it.
- **Journal in today's file.** Write into `journals/YYYY-MM-DD.md` (create
  it on the first entry of the day; headings inside are free — `## HH:MM`
  or a title, newest first). **Before the first entry of a new day, move
  yesterday's file to `journals/archive/YYYY/MM/`**
  (`mkdir -p _brain/journals/archive/YYYY/MM && git mv …`) — the contract
  blocks a commit with two unarchived days.
- **To-dos live in `todo/open.md`.** A task that surfaces mid-work goes
  there as `- [ ] …`. When it is done, tick it `- [x] … (done: YYYY-MM-DD)`
  and move the line to `todo/archive/YYYY-MM-DD.md` (a `type: todo` doc
  for that day; create it on first use) — the same day or the next, the
  contract insists. Never edit the archive afterwards.
- **A procedure that works becomes a skill**: `brainpick skill new <name>`
  scaffolds `skills/<name>.md` as `type: skill` with `depends_on` and
  `tools` (paths to the deterministic scripts it drives — put them in
  `skills/tools/`). A `playbook` is a how-to for humans and is not a skill.
- **DRY by pointer.** When you distil, the less distilled doc gains a
  pointer to the more distilled one ("now covered by [skill]") — never a
  copy. The journal points to what it changed and never restates it.
- **Raw stays clean.** Drop source material into `raw/` with a kebab-case
  name that says what it is, list it in `raw/index.md`, and clean up after
  yourself: prune what you have distilled or found worthless. Raw is
  valuable — it is what claims ground on — only while it stays greppable.
- **Ground every claim inline**, Wikipedia-style, with a plain link: a
  journal entry (a decision we made), an external page, another brain
  (`brain://slug-id/path`), or say in words that it is an assumption.
- **Reading a less distilled layer is a distillation opportunity.** If the
  answer was in the journal, ask whether it should now be knowledge.
- **Bump `timestamp`** on every change; keep `type`, `title`, `description`.
  The timestamp is also what the half-life reads: memories fade in search
  ranking as they age, slowly by default (`[half_life]` in
  `brainpick.toml`). When you notice the lists silting up with stale
  material, steepen the curve there — shorter days for `journals` or
  `todo`, or a per-page `half_life:` in frontmatter — rather than deleting;
  nothing is ever hidden, it only ranks lower.
- **Commit and push what you changed** (the contract checks it on commit)
  so the next reader's pull brings your version — memory that stays on one
  machine is not shared memory.

## Several brains: subsidiarity

When brains conflict: the closest wins. Update both. Then decide — keep the
information duplicated (readers of the farther brain may not have the
closer one) or replace it with a `brain://` pointer. Record the episode in
the journal of the brain that changed.

## Where this comes from

Evergreen concepts live in [Knowledge](../knowledge/index.md); what happened
and when, in the [Journals](../journals/index.md). The brain format and its
reasoning live in brainpick's wiki:
{url}/blob/main/docs/brain.md — data flow, grounding, subsidiarity, and what
is fixed for life versus cheap to change. Serve this brain with
`brainpick init`, then the `brain_*` MCP tools.
"""

_SEED_CONFIG = """# brainpick.toml — how this brain is compiled and served (SHARED policy, committed).
# Machine-local model endpoints live in brainpick.local.toml beside this file —
# it deep-merges over this one and stays out of git. Run `brainpick init` to
# detect backends and mint a [bundle] id (a stable address for this brain).
spec = "0.1"

[bundle]
root = "{brain}"
exclude = ["raw/*"]     # source material stays greppable but never surfaces in results

[index]
mode = "section"        # brainpick owns a generated block at the end of index.md

[brain]
format = {format}              # the brainpick brain format (spec/85): day journals, todo/ in the brain
audience = "personal"   # personal | team | public — who this brain is written for
# origin = ""           # canonical git URL, once this repo has one
# readers = []          # for team: who reads it, by handle or role

# Memories fade — a ranking factor, never a deletion: a doc's search score is
# multiplied by 2^(-age/half_life) on its `timestamp`, floored so it stays
# recallable. Slow by default. When the lists silt up with stale material,
# STEEPEN the curve here (fewer days) instead of deleting; a single page can
# pin itself with `half_life: 0` in its frontmatter or let go with `half_life: 7`.
[half_life]
default = {half_life}           # days; 0 = never fades
[half_life.folders]     # folder → days, the most nested folder wins
journals = 180          # episodic memory fades first
todo = 90               # an open list should be a fresh list
skills = 0              # procedural memory never fades
"""

# Ships with the template: the brain's custom checks (henxels_checks.py). The
# log_headings_are_dates check is the same one the OKF wiki template scaffolds.
BRAIN_CHECKS_PY = '''"""Custom checks for the brain (scaffolded by `henxels init --template brainpick-brain`)."""

import datetime
import re

import yaml

from henxels import statement

_SECTION = re.compile(r"^##\\s+(.+?)\\s*$")
_DAY = re.compile(r"^(\\d{4})-(\\d{2})-(\\d{2})\\.md$")
_CHECKBOX = re.compile(r"^\\s*[-*+]\\s+\\[([ xX])\\]\\s+(.*?)\\s*$")
_DONE = re.compile(r"\\(done:\\s*(\\d{4}-\\d{2}-\\d{2})\\)\\s*$")


def _folder(param):
    return str(param).strip().removeprefix("./").strip("/")


def _frontmatter(text):
    """The leading ``---`` YAML block as a dict (empty when absent or unparseable)."""
    if not text or not text.startswith("---"):
        return {}
    lines = text.splitlines()
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}
    try:
        data = yaml.safe_load("\\n".join(lines[1:end]))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


@statement("log_headings_are_dates", help="log.md sections are '## YYYY-MM-DD' headings, newest first")
def log_headings_are_dates(file, scope):
    dates, problems = [], []
    for line in (scope.read_text(file) or "").splitlines():
        m = _SECTION.match(line)
        if not m:
            continue
        try:
            dates.append(datetime.date.fromisoformat(m.group(1)))
        except ValueError:
            problems.append(f"section '{m.group(1)}' — head log sections with an ISO date: ## YYYY-MM-DD")
    if dates != sorted(dates, reverse=True):
        problems.append("order the date sections newest first")
    return problems


@statement("skill_tools_exist", help="every path a skill lists under `tools:` exists, relative to the bundle root")
def skill_tools_exist(param, file, scope):
    """brainpick indexes and points at a skill's tools (spec/85); a path that lands
    nowhere is a broken promise. `param` is the bundle root (./_brain)."""
    root = _folder(param)
    tools = _frontmatter(scope.read_text(file)).get("tools") or []
    if not isinstance(tools, list):
        return f"{file} — `tools:` must be a list of bundle-relative paths"
    missing = [t for t in tools if not scope.exists(f"{root}/{str(t).lstrip('/')}")]
    return [f"{file} — tool {t} does not exist under {root}/ (add it or drop it from `tools:`)" for t in missing]


@statement("archived_journals_sit_under_year_month",
           help="archived journal days live at archive/YYYY/MM/YYYY-MM-DD.md, the folders matching the name")
def archived_journals_sit_under_year_month(param, file, scope):
    """`param` is the archive folder (./_brain/journals/archive)."""
    archive = _folder(param)
    rel = file[len(archive) + 1:] if file.startswith(archive + "/") else file
    name = rel.rsplit("/", 1)[-1]
    m = _DAY.match(name)
    if not m:
        return f"{file} — name an archived day YYYY-MM-DD.md"
    want = f"{m.group(1)}/{m.group(2)}/{name}"
    if rel != want:
        return f"{file} — move it to {archive}/{want} (the day roll keeps archive/YYYY/MM/)"
    return None


@statement("done_todos_are_archived",
           help="a [x] item in open.md carries (done: YYYY-MM-DD) and leaves for archive/YYYY-MM-DD.md the next day; "
                "the archive is day files holding only done items")
def done_todos_are_archived(param, file, scope):
    """`param` is the todo folder (./_brain/todo)."""
    todo = _folder(param)
    rel = file[len(todo) + 1:] if file.startswith(todo + "/") else file
    problems = []
    items = [(m.group(1).lower() == "x", m.group(2)) for m in map(_CHECKBOX.match, (scope.read_text(file) or "").splitlines()) if m]
    if rel == "open.md":
        today = datetime.date.today()
        for done, text in items:
            if not done:
                continue
            m = _DONE.search(text)
            if not m:
                problems.append(f"{file} — '{text[:40]}' is ticked but undated: end it with (done: YYYY-MM-DD)")
                continue
            day = m.group(1)
            if datetime.date.fromisoformat(day) < today:
                problems.append(f"{file} — '{text[:40]}' was done {day}: move the line to {todo}/archive/{day}.md")
        return problems
    if rel.startswith("archive/"):
        name = rel.rsplit("/", 1)[-1]
        if "/" in rel[len("archive/"):] or not _DAY.match(name):
            return f"{file} — an archived to-do file is {todo}/archive/YYYY-MM-DD.md, the day its items were closed"
        for done, text in items:
            if not done:
                problems.append(f"{file} — '{text[:40]}' is still open: it belongs in {todo}/open.md, not the archive")
        return problems
    return None
'''

GITIGNORE_ENTRIES = ("_temp/", "brainpick.local.toml", ".brainpick/")


def brain_fragment() -> str:
    """The brain henxels, appended to the detected starter's `henxels:` list."""
    return _BRAIN.substitute(brain=BRAIN_DIR, url=BRAINPICK_URL)


def brain_seeds() -> dict[str, str]:
    today = datetime.date.today().isoformat()
    b = BRAIN_DIR
    return {
        f"{b}/index.md": _SEED_INDEX,
        f"{b}/log.md": _SEED_LOG.format(today=today),
        f"{b}/knowledge/index.md": _SEED_KNOWLEDGE_INDEX,
        f"{b}/skills/using-the-brain.md": _SEED_SKILL.format(today=today, url=BRAINPICK_URL),
        f"{b}/journals/index.md": _SEED_JOURNALS_INDEX,
        f"{b}/journals/{today}.md": _SEED_JOURNAL_DAY.format(today=today),
        f"{b}/todo/index.md": _SEED_TODO_INDEX,
        f"{b}/todo/open.md": _SEED_TODO_OPEN.format(today=today),
        f"{b}/raw/index.md": _SEED_RAW_INDEX,
        f"{b}/vision/index.md": _SEED_VISION_INDEX,
        f"{b}/plans/index.md": _SEED_PLANS_INDEX,
        f"{b}/conventions/index.md": _SEED_CONVENTIONS_INDEX,
        "brainpick.toml": _SEED_CONFIG.format(brain=b, format=BRAIN_FORMAT, half_life=HALF_LIFE_DEFAULT_DAYS),
    }


def ensure_gitignored(root: Path, entries: tuple[str, ...] = GITIGNORE_ENTRIES) -> bool:
    """Append missing entries to .gitignore (creating it if needed); never rewrite what's there."""
    gi = root / ".gitignore"
    existing = gi.read_text(encoding="utf-8") if gi.exists() else ""
    lines = {line.strip() for line in existing.splitlines()}
    missing = [e for e in entries if e not in lines and e.rstrip("/") not in lines]
    if not missing:
        return False
    sep = "" if not existing or existing.endswith("\n") else "\n"
    gi.write_text(existing + sep + "\n".join(missing) + "\n", encoding="utf-8")
    return True
