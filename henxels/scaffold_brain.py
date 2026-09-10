"""The brainpick brain starter (``henxels init --template brainpick-brain``).

A brain is a wiki meant to be an agent's memory: ``_brain/`` with six memory-type
folders (knowledge, skills, journal, vision, plans, conventions), a declared data
flow (journal → knowledge → skills, read in reverse; a settled decision → a
conventions page alongside it), inline grounding, and a first skill that teaches
the agent how to use and improve it. brainpick's spec/85 fixes
the format; this template scaffolds it — structure + contract live here, serving
(``brainpick init``, compile, the ``brain_*`` MCP tools) is brainpick's half of the
handoff: https://github.com/benquemax/brainpick
"""

from __future__ import annotations

import datetime
from pathlib import Path
from string import Template

BRAIN_DIR = "_brain"
BRAIN_FOLDERS = ("knowledge", "skills", "journals", "vision", "plans", "conventions", "raw")
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

  - henxel: "Folders are memory types — knowledge, skills, journals, vision, plans, conventions — one job each; raw/ is source material"
    why: >
      knowledge/ is semantic memory (evergreen concepts), skills/ procedural
      (distilled, actionable procedures), journals/ episodic (one file per
      month, dated sections), vision/ direction (a book), plans/ decided
      work, conventions/ decided rules and principles for HOW things get
      done (standing policy — naming, process, contracts — not a specific
      task like plans/, not a step-by-step procedure like skills/). raw/ is
      not a memory type: it is undistilled source material (transcripts,
      exports, clippings) that knowledge grounds on — governed for order,
      exempt from OKF, and excluded from brainpick's results. Nothing is
      replicated across layers. A memory type that does not fit these seven
      is a `type` value or a sub-folder, never an eighth sibling. Read
      skills/ first — it is the most distilled, tested and pure layer —
      then conventions/, then knowledge/, then journals/; grep raw/ only to
      ground or to distil.
      Data flow architecture: $url/blob/main/docs/data-flow-architecture.md
    in: ./$brain
    required_files: index.md
    required_subfolders: [knowledge, skills, journals, vision, plans, conventions, raw]
    only_these_subfolders: [knowledge, skills, journals, vision, plans, conventions, raw]

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
    except: ["**/index.md", "**/log.md", "**/skilltree.md", "$brain/journals/**", "$brain/raw/**"]
    allowed_filetypes: .md
    filename_casing: kebab-case
    required_frontmatter: [type, title, description]

  - henxel: "Freshness is explicit — timestamp is a real ISO 8601 datetime bumped whenever a doc changes"
    in: ./$brain/*
    except: ["**/index.md", "**/log.md", "**/skilltree.md", "$brain/journals/**", "$brain/raw/**"]
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

  - henxel: "Skills are actionable playbooks that form a dependency tree — declare depends_on, never edit skilltree.md"
    why: >
      A skill is a procedure a reader follows (type: playbook). It lists the
      skills it assumes in `depends_on` frontmatter (bundle-relative .md
      paths; omit it or use `[]` when it assumes nothing). skilltree.md is
      generated from those edges by brainpick — edit the skills, never the
      tree. A skill with `export: agent-skill` is also written out as a
      harness-loaded SKILL.md, so the brain's procedures reach the agent
      before it decides anything.
    in: ./$brain/skills/*
    except: ["**/index.md", "**/skilltree.md"]
    frontmatter_values:
      type: [playbook]

  - henxel: "One journal file per month — journals/YYYY-MM.md — with a ## YYYY-MM-DD section per day, newest first"
    why: >
      Journals are episodic memory: what happened, when. A month per file
      caps the length forever; a day per section keeps it navigable. Every
      heading is an ISO date. An entry links forward to the knowledge or
      skill it changed instead of restating it (DRY by pointer, in the
      direction of distillation); when you distil an entry, add the pointer
      to it. Journals are logs, not concept docs: no frontmatter.
    in: ./$brain/journals
    except: ./$brain/journals/index.md
    allowed_filetypes: .md
    filename_matches_regex: '^\\d{4}-\\d{2}\\.md$$'
    no_frontmatter: true
    log_headings_are_dates: true    # custom check, lives in henxels_checks.py

  - henxel: "Only the current month stays in journals/ — earlier months move to journals/archive/"
    why: >
      History without the bulk: when a new month starts, move last month's
      file to journals/archive/ (same name; mkdir -p it the first time)
      before writing the first entry.
      Two unarchived months block the commit, so the roll cannot be
      forgotten. Archived months are read-only history and keep their
      dated-section shape; brainpick indexes both.
    in: ./$brain/journals
    except: ./$brain/journals/index.md
    only_these_subfolders: [archive]
    max_files: 1

  - henxel: "Archived journals are month files with dated sections, untouched otherwise"
    in: ./$brain/journals/archive
    allowed_filetypes: .md
    filename_matches_regex: '^\\d{4}-\\d{2}\\.md$$'
    no_frontmatter: true
    log_headings_are_dates: true

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
      Undecided ideas belong in _todo.md (a task) or journals/ (an insight),
      not here.
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

  - henxel: "_todo.md lives beside the brain, gitignored — project management is not knowledge"
    why: >
      Tasks that surface mid-work go to _todo.md instead of derailing the
      task at hand. It is neither evergreen nor an episode, so it is not in
      $brain/. Per-developer, not shared: gitignored, so it is never a
      merge-conflict magnet and never silently public. Check it before
      planning any new work — it may already flag a known imperfection, a
      planned deprecation, or something overlapping the task, and building
      more onto a feature already marked for removal wastes the work twice.
    in: .
    required_files: _todo.md
    level: warn
    run_before_commit: git check-ignore -q _todo.md

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

Episodic memory — what happened, when. One file per month (`YYYY-MM.md`), one
`## YYYY-MM-DD` section per day, newest first. Only the current month lives
here; when a new month starts, move the previous file into `archive/`
(`mkdir -p` it the first time) before writing the first entry. Entries point to the knowledge or skill they changed
instead of restating it.
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

_SEED_JOURNAL_MONTH = """# {month}

## {today}

* Brain created. First skill: [Using the brain](../skills/using-the-brain.md).
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
each listed here. Undecided ideas belong in `_todo.md` or the journal.

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
type: playbook
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
   The current month is `journals/YYYY-MM.md`; older months are in
   `journals/archive/`.
6. **`raw/`** — undistilled source material. Not in search results; grep it
   to ground a claim or to distil something new.

With brainpick: `brain_overview` first, then `brain_search`, then
`brain_read`. Grep only after the brain comes up short.

## Writing: distil upward, point, ground

- **Information flows `journals/` → `knowledge/` → `skills/`.** An episode
  becomes a concept when it settles; a concept becomes a skill when it has
  been carried out and works. A decision that settles into a standing rule
  — applied broadly, not just this one time — becomes a `conventions/` page
  instead, `type: decision`, alongside that flow rather than inside it.
- **Journal under today's date.** Write into `journals/YYYY-MM.md` under a
  `## YYYY-MM-DD` heading (newest first; add today's if missing). **When a
  new month starts, move last month's file to `journals/archive/` first**
  (`mkdir -p _brain/journals/archive && git mv …`) — the contract blocks a
  commit with two unarchived months.
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
format = 1              # the brainpick brain format (spec/85)
audience = "personal"   # personal | team | public — who this brain is written for
# origin = ""           # canonical git URL, once this repo has one
# readers = []          # for team: who reads it, by handle or role
"""

_SEED_TODO = (
    "# Parking lot\n\n"
    "Tasks that surface mid-work but fall outside its scope land here instead of\n"
    "derailing the task at hand. Project management, not knowledge — that is why\n"
    "this file lives beside the brain, not in it. Per-developer and gitignored —\n"
    "never committed, never a merge-conflict magnet. Check it before planning\n"
    "new work: it may already flag a known imperfection, a planned deprecation,\n"
    "or something overlapping the task.\n"
)

GITIGNORE_ENTRIES = ("_temp/", "brainpick.local.toml", ".brainpick/", "_todo.md")


def brain_fragment() -> str:
    """The brain henxels, appended to the detected starter's `henxels:` list."""
    return _BRAIN.substitute(brain=BRAIN_DIR, url=BRAINPICK_URL)


def brain_seeds() -> dict[str, str]:
    today = datetime.date.today().isoformat()
    month = today[:7]
    b = BRAIN_DIR
    return {
        f"{b}/index.md": _SEED_INDEX,
        f"{b}/log.md": _SEED_LOG.format(today=today),
        f"{b}/knowledge/index.md": _SEED_KNOWLEDGE_INDEX,
        f"{b}/skills/using-the-brain.md": _SEED_SKILL.format(today=today, url=BRAINPICK_URL),
        f"{b}/journals/index.md": _SEED_JOURNALS_INDEX,
        f"{b}/journals/{month}.md": _SEED_JOURNAL_MONTH.format(month=month, today=today),
        f"{b}/raw/index.md": _SEED_RAW_INDEX,
        f"{b}/vision/index.md": _SEED_VISION_INDEX,
        f"{b}/plans/index.md": _SEED_PLANS_INDEX,
        f"{b}/conventions/index.md": _SEED_CONVENTIONS_INDEX,
        "_todo.md": _SEED_TODO,
        "brainpick.toml": _SEED_CONFIG.format(brain=b),
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
