---
title: Enforcing the Open Knowledge Format (OKF)
summary: A worked contract for OKF knowledge bundles — frontmatter conformance, reserved files, bundle-absolute links, timestamps, and a custom check for update logs.
---

# Enforcing the Open Knowledge Format (OKF)

The [Open Knowledge Format (OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
is Google's convention for **knowledge bundles**: a tree of markdown *concept documents*
that LLMs and agents read — and increasingly write. It formalizes the LLM-wiki pattern.
Each concept doc opens with YAML frontmatter (`type` is the one required field),
cross-links assert relationships between concepts, and two reserved filenames organize
the rest: `index.md` (a directory's table of contents) and `log.md` (its update history).

OKF puts the burden on producers by design: consumers MUST tolerate almost anything, so
a bundle is only as good as the discipline of whoever maintains it. That is henxels' job
description. The contract below makes the OKF v0.1 conventions impossible to break *by
accident* — and because the contract is mirrored into `AGENTS.md`, the agent that
maintains the wiki reads the format's rules before it writes a single page.

## The contract

Say the bundle lives in `wiki/` (any folder works — the spec blesses a whole repo, a
subdirectory of a bigger one, or an archive):

```yaml
settings:
  confirm_before_deleting: { over_lines: 10 }   # knowledge doesn't vanish in a diff slip
  warn_about_similar_files:                     # one concept, ONE document — update it,
    above: 0.82                                 # don't clone a near-duplicate
    ignore: ["**/index.md", "**/log.md"]

henxels:
  - henxel: "Every concept doc is kebab-case markdown with OKF frontmatter (type is the one MUST)"
    in: ./wiki/*
    except: ["**/index.md", "**/log.md", "wiki/references/*"]
    allowed_filetypes: .md
    filename_casing: kebab-case
    required_frontmatter: [type, title, description]
    frontmatter_values:
      type: [BigQuery Table, API Endpoint, Metric, Playbook]

  - henxel: "timestamp is a real ISO 8601 datetime and is bumped when a doc changes"
    in: ./wiki/*
    except: ["**/index.md", "**/log.md", "wiki/references/*"]
    frontmatter_dates: { timestamp: datetime }
    bump_updated_on_change: timestamp

  - henxel: "Every link lands — bundle-absolute (/tables/customers.md) and relative alike"
    in: ./wiki/*
    rooted_links_resolve: ./wiki
    links_resolve: true

  - henxel: "A concept is a node in the knowledge graph, not an orphan"
    in: ./wiki/*
    except: ["**/index.md", "**/log.md", "wiki/references/*"]
    min_outbound_links: 1

  - henxel: "OKF reserved files stay frontmatter-free (the bundle root may declare okf_version)"
    in: ["./wiki/**/index.md", "./wiki/**/log.md"]
    except: ./wiki/index.md
    no_frontmatter: true

  - henxel: "Update logs are date-sectioned, newest first"
    in: ./wiki/**/log.md
    log_headings_are_dates: true      # the one custom check — see below

  - henxel: "The bundle root has an index and every top-level concept is listed in it"
    in: ./wiki
    except: "**/log.md"
    required_files: index.md
    referenced_in: wiki/index.md
```

## What each henxel enforces, against the spec

- **Concept docs** — OKF conformance says every non-reserved `.md` must carry parseable
  frontmatter with a **non-empty** `type`. `required_frontmatter` enforces exactly that
  (an empty `type:` counts as missing, and a file whose frontmatter doesn't parse has no
  keys at all). `title` and `description` are the spec's top recommended fields — the
  ones consumers display — so the same henxel requires them. `frontmatter_values` pins
  the `type` vocabulary: OKF lets each producer pick its own descriptive types, and
  pinning yours keeps the taxonomy from fraying as the wiki grows. The `except:` carves
  out the reserved files and `references/`, where citation targets (PDFs, exports) may
  live.
- **Timestamps** — `timestamp` is the spec's "last meaningful change" field, an ISO 8601
  datetime; `frontmatter_dates: { timestamp: datetime }` validates the format, and
  `bump_updated_on_change` (diff-aware, so it acts at commit time) rejects a commit that
  edits a concept without touching its `timestamp`.
- **Links** — OKF recommends bundle-absolute links (`/tables/customers.md`, resolved
  from the bundle root) because they survive refactors; `rooted_links_resolve: ./wiki`
  checks them, and `links_resolve` covers the relative form. Consumers must *tolerate*
  broken links — that's no reason to ship any.
- **Connectivity** — links are the edges of the knowledge graph, so `min_outbound_links`
  keeps any concept from becoming an island.
- **Reserved files** — `index.md` and `log.md` carry no frontmatter, with one carve-out
  straight from the spec: the bundle-root `index.md` alone MAY declare `okf_version`.
- **Indexes** — the bundle root keeps an `index.md` that lists every top-level concept
  (`referenced_in`). OKF's progressive disclosure means each subdirectory can keep its
  own index; add one such henxel per directory you want held to that bar.

## The one corner that needs a custom check

No built-in reads `log.md`'s section structure (date-grouped entries, newest first).
That's a ten-line custom check in `henxels_checks.py` at the repo root — auto-loaded, no
config:

```python
import datetime
import re

from henxels import statement

_SECTION = re.compile(r"^##\s+(.+?)\s*$")


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
```

`henxels create-new-statement log_headings_are_dates` scaffolds a stub like this; see
[Custom checks](custom-checks.md) for the injection API. If your check proves reusable
beyond one repo, send it upstream with `henxels contribute`.

## What it looks like when it holds

A conformant concept document, for reference:

```markdown
---
type: BigQuery Table
title: customers
description: One row per customer account.
resource: bigquery://project/dataset/customers
timestamp: 2026-06-12T14:30:00Z
---

# Schema

| column | type  | notes       |
| ------ | ----- | ----------- |
| id     | STRING | primary key |

Feeds the [revenue metric](/metrics/revenue.md).
```

Break any rule — an empty `type:`, frontmatter on a nested `index.md`, a dead
`/tables/orders.md` link, an unlisted concept — and `henxels check` answers with the
henxel's sentence plus a per-file instruction an agent can act on. The similarity
warning rounds it out: when a writer (human or model) is about to create a fifth
near-duplicate page about the same concept, henxels tells it to update the existing one
instead. One concept, one document — which is the whole point of OKF.
