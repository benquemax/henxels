---
title: Settings
summary: The settings block holds behaviours — staging, push, and delete protections plus similarity and large-file warnings — the parts of the contract that aren't tests.
---

# Settings

`settings:` is for **behaviours**, not tests: protections that intercept a git action, and
awareness knobs. Statements go in the `henxels:` list; behaviours go here.

```yaml
settings:
  ask_me_before_staging: true
  confirm_before_push: true
  confirm_before_deleting: { over_lines: 5 }
  warn_about_similar_files: { above: 0.85, ignore: ["**/__init__.py"] }
  warn_about_large_files: { over: 8000 tokens, ignore: ["assets/**"] }
```

## ask_me_before_staging

Reminds the agent not to run `git add` / `git commit` / `git push` itself, but to ask you
to review and stage. Git has no pre-add hook, so this is **steering**, surfaced loudly in
the `AGENTS.md` digest. For hard enforcement in OpenCode, run `henxels integrate opencode`
(see [Agent integrations](agent-integrations.md)).

## confirm_before_push

Blocks `git push` until you run `henxels bless push`. This one is **enforced** by the
pre-push hook. See [Guards and bless](guards-and-bless.md).

## confirm_before_deleting

Blocks a commit that deletes files **or** removes more than `over_lines` net lines, until
`henxels bless delete`. Small agents lose rows through diff-edit mistakes, so the loss has
to be deliberate. Accepts `true` (default threshold) or `{ over_lines: N }`.

## warn_about_similar_files

Warns (never blocks) when a changed file is a near-copy of a committed one — the
anti-scatter nudge that pushes an agent to update an existing file instead of cloning it.
`above` is the similarity ratio (0–1); `ignore` is a list of globs to skip.

**Changed-file scans go deep**: every staged (or explicitly listed) file is
compared against the whole committed corpus, so even a doc re-written from
scratch about the same topic — same vocabulary, not one shared line — is caught
at the moment it's committed. **Whole-repo scans** (`check --all`, the push
gate) would be O(N²) minutes at that depth, so they instead work the way git's
rename/copy detection does: a cheap pass over identical (whitespace-trimmed)
lines shortlists candidate pairs, and only the shortlist is diffed. Its blind
spot — pairs sharing almost no whole lines — is exactly what the deep scan
already warned about when those files were committed.

Both depths stay fast because a warning needs *a* match, not the closest one:
hopeless pairs are pruned by two cheap upper bounds (length, then character
frequency), the most promising committed file is diffed first, and one hit ends
the scan for that file. A commit of 98 generated near-copies against a
150-file corpus drops from the better part of an hour to well under a second.

The scan always runs to completion by default — a duplicate is worth knowing
about even when the scan takes minutes. If you'd rather cap it (a huge repo, a
hot pre-commit path), set `budget` to seconds (`30`), or `"30s"`, `"5m"`,
`"1h"`. When the budget runs out you get the warnings found so far plus one
more saying the results are partial; the durable fix is `ignore` globs for
generated/data paths, which remove them from both sides of the comparison.

`at_most` (default 20) caps how many pairs are listed before the rest collapse into a
single count. Importing an archive or a vendored tree can make hundreds of files resemble
each other, and a warning nobody can read is a warning nobody reads. If a whole folder is
legitimately full of near-copies, `ignore` it rather than raising the cap.

## warn_about_large_files

Warns when a file exceeds a size threshold. `over` is unit-aware: `8000 tokens`,
`200 lines`, or `3 kb` (`b`, `kb`, `mb`, `gb`, `tokens`, `lines`; optional space; the unit
is required). Tokens — the unit an agent's context window is measured in — are a
dependency-free estimate (`chars / 4`) and are always labelled `(estimated)`. `ignore`
skips globs. It warns, never blocks.

## Where settings are read

Behaviours run during `henxels check` and inside the git hooks. They are not statements, so
they never appear in the `henxels:` list — and a custom statement that uses a settings name
is flagged (see [Custom checks](custom-checks.md)).
