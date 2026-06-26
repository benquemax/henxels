---
name: henxels
description: Keep edits faithful to this repo's structure contract. Use BEFORE creating or moving a file, and AFTER editing, whenever a henxels.yaml is present at the repo root.
---

# henxels

This repo has a structure **contract** in `henxels.yaml`. Each rule is a *henxel*.
Disobeying a henxel is only allowed by editing the contract — never by working around it.

## Before you create or move a file

Run:

```bash
henxels explain <path>
```

It prints, in plain words, every henxel that governs that location (naming, allowed
filetypes, required frontmatter, where things must/can't live). Write the file to
satisfy it. If a check feels wrong, change `henxels.yaml` — that is the sanctioned escape.

## After you edit

Run:

```bash
henxels check <path>      # or: henxels check --staged
```

Exit code 1 means a henxel held you back; the output tells you which file and what to do.
Fix it (or amend the contract) before moving on.

## Git etiquette

- `git push` is guarded: run `henxels bless push` first, then push.
- Deleting files or many lines is guarded: run `henxels bless delete` first.
- Don't disable the git hooks; they enforce the contract for everyone.

## Discover & extend

- `henxels catalogue` — the statements available to use in a henxel.
- `henxels create-new-statement <name>` — scaffold a custom check.
- If a custom check is reusable beyond this repo, contribute it: `henxels contribute`.
