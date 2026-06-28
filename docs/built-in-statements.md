---
title: Built-in statements
summary: The standard library of statements that ship with henxels, grouped by what they verify — naming, structure, content, links, size, secrets, and change.
---

# Built-in statements

Run `henxels catalogue` to browse the standard library with one-line descriptions. This
guide groups them by concern. A scalar stands in for a one-item list everywhere, so you
rarely write `[x]`.

## Naming

- **`filename_casing`** — file names use a convention: `snake_case`, `kebab-case`,
  `camelCase`, `PascalCase`, `SCREAMING_SNAKE_CASE`, or `any`. A list means *any of*.
- **`filename_matches_regex`** — every file name matches a regex (a list means *any of*).

## Structure

- **`allowed_filetypes`** — every file is one of these extensions or globs (a list is *or*).
- **`required_files`** — these files must exist in the scope.
- **`required_subfolders`** — these subfolders must exist.
- **`only_these_subfolders`** — only these immediate subfolders may exist.
- **`forbidden_files`** — none of these files or globs may exist.
- **`forbidden_subfolders`** — none of these subfolders may exist.
- **`must_not_exist`** — the scoped location must not exist at all.

## Content and frontmatter

- **`required_frontmatter`** — markdown files declare these frontmatter keys (a list is
  *all*). Checks presence, not value.
- **`frontmatter_dates`** — the named frontmatter fields are valid ISO dates
  (`YYYY-MM-DD`).
- **`frontmatter_values`** — fields hold values from an allowed set. A scalar field must be
  in the set; a list field must be a subset of it. One statement covers an enum (`type`)
  and a taxonomy (`tags`).
- **`frontmatter_sha256_matches`** — the named frontmatter field equals the SHA-256 of the
  body below the frontmatter (integrity for ingested sources).
- **`markdown_lint`** — markdown passes pymarkdownlnt. It is optional: install the
  `[markdown]` extra (`pip install "henxels[markdown]"`). Without it, the check passes and
  `henxels doctor` nudges you to install it.
- **`markdown_links_absolute`** — markdown links and images are absolute URLs, not
  repo-relative (so they survive on PyPI and npm).

## Links

These suit a wiki or any cross-linked markdown:

- **`links_resolve`** — every relative internal link points at a real file.
- **`links_are_relative`** — internal links are relative, not absolute paths.
- **`min_outbound_links`** — each page links out to at least N other pages.
- **`referenced_in`** — every page in scope is linked from an index file (`index.md`).

## Size

- **`max_lines`** — each file in scope stays under a line budget. (For a repo-wide size
  *warning* in tokens, lines, or bytes, use the `warn_about_large_files` setting instead —
  see [Settings](settings.md).)

## Secrets

- **`no_secrets`** — files contain no credentials (private keys, API tokens, passwords). It
  is conservative on purpose; narrow the scope with `except:` to allow a sanctioned vault.

## Change (diff-aware)

These ask for the staged diff, so they only act at commit time:

- **`append_only`** — staged edits only add lines to the end; existing lines never change.
- **`immutable`** — files here can be added but never modified once committed.
- **`bump_updated_on_change`** — when a page's content changes, its date field must change
  too.
Two commit-time **reminders** that only fire when relevant — so they never nag on an
unrelated commit. Pair both with `level: warn`.

- **`must_be_in_sync`** — *symmetric*. Groups of files/folders that change together; warns
  if some members changed and others didn't. Use it for genuinely-coupled files, where a
  change to any one should touch the rest — translation files, a schema and its generated
  client, a lockfile and its manifest. A flat list is one group; a list of lists is several.

```yaml
  - henxel: "Translations stay in sync"
    must_be_in_sync:
      - [i18n/en.json, i18n/fi.json, i18n/de.json]
      - [api/schema.json, api/generated-client.ts]
    level: warn
```

- **`changed_with`** — *directional*. When files matching `when` are staged, files matching
  `expect` should change too — but not the reverse. Use it when the relationship has a
  direction, like code → docs (a docs-only typo fix shouldn't be nagged to change code):

```yaml
  - henxel: "Behaviour changes update the docs"
    changed_with:
      when: src/**
      expect: [docs/**, README.md]
    level: warn
```

Rule of thumb: reach for `must_be_in_sync` when the files are *peers* that always move
together, and `changed_with` when one *follows* the other.

## Commands and meta

- **`run_before_commit`** / **`run_before_push`** — a shell command (tests, lints) that
  must pass at that git stage.
- **`well_formed_statements`** — every statement defined in this repo has a `help=` and a
  test. The quality bar for contributing a statement upstream.

For statements not covered here, see [Custom checks](custom-checks.md).
