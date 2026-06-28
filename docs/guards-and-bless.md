---
title: Guards and bless
summary: How the push and delete protections work — they don't forbid, they make a hard-to-undo action a conscious, one-time act via henxels bless.
---

# Guards and bless

Guards protect actions that are hard to take back. They don't forbid — they make you mean
it. The escape is a deliberate, non-standard verb: `henxels bless <action>`, which mints a
one-time token the git hook consumes.

## The push guard

With `confirm_before_push: true`, the pre-push hook blocks `git push`:

```text
$ git push
✗ Push is guarded — a push is hard to take back
    → henxels bless push   (then push again)
```

`henxels bless push` writes a one-time token bound to the current `HEAD` commit under
`.git/henxels/`. The next push consumes it and goes through; a reflexive retry can't reuse
it. If `HEAD` moves, the token no longer matches.

## The delete guard

With `confirm_before_deleting`, the pre-commit hook blocks a commit that loses information —
**deleted files and net-removed lines** (computed from the staged diff). A configurable
`over_lines` threshold avoids nagging on small edits:

```text
✗ Information loss is guarded — deletion should be deliberate
    src/api/handlers.py — 12 lines removed
    → henxels bless delete   (then commit again)
```

`henxels bless delete` mints a token bound to the exact set of staged deletions. Change the
deletions and the token no longer matches, so you confirm what you actually meant to lose.

## Why a token, not a flag

A token is single-use and bound to a fingerprint (the `HEAD` sha for push, the staged
deletions for delete). That means blessing is specific to *this* action — you can't bless
once and have every future push or deletion sail through. The conscious act is the point.

## Staging

`ask_me_before_staging` is a *steering* behaviour, not a guard: git has no pre-add hook, so
henxels can't block `git add` directly. It surfaces the rule in the `AGENTS.md` digest, and
the OpenCode integration can enforce it at the tool layer. See
[Agent integrations](agent-integrations.md) and [Settings](settings.md).

## Hooks

The hooks are installed by `henxels init` and verified by `henxels doctor`. They resolve
henxels from the project's environment first (a `.venv`, then a global install), so the
hook runs the version your project pins. Re-run `henxels init` after upgrading henxels to
refresh them — see [Upgrading](upgrading.md).
