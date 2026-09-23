---
title: Natural-language henxels
summary: Rules written as plain sentences and judged by a language model — make_sure_that, @path file references, the judge setting (any OpenAI-compatible endpoint, local or remote), confidence-driven severity, and what it will never do.
---

# Natural-language henxels

Some rules can't be reduced to a glob or a regex:

- "Behaviour changes are *described* in the docs, not just touched."
- "A journal entry says what was decided, not only what was done."
- "New CLI flags are documented in the README."

Henxels already asks you to write every rule as a sentence a small model can read.
`make_sure_that` closes the loop: the sentence *is* the check. At commit time the staged
changes in scope are shown to a language model — the **judge** — which answers whether
the sentence holds, why, and how sure it is.

```yaml
settings:
  judge:
    base_url: http://localhost:11434/v1     # Ollama, llama.cpp, vLLM, LM Studio, OpenAI, …
    model: qwen3:8b
    api_key_env: OPENAI_API_KEY             # optional; unset = no key sent

henxels:
  - henxel: "Behaviour changes are described in the docs"
    in: [./src/*, ./docs/*, ./README.md]
    why: A doc that lies is worse than no doc.
    make_sure_that: true                    # judge this henxel's own sentence (+ why)
    level: warn
```

`make_sure_that: true` judges the henxel's own sentence and passes `why:` along as
background. A string — or a list of strings — judges those sentences instead, so one
henxel can carry several claims:

```yaml
  - henxel: "Python changes are reviewable"
    in: ./src/*
    make_sure_that:
      - every new public function has a docstring
      - no debugging prints were left in
```

## Pointing at a file: `@path`

A sentence can hand the judge a file with `@path` (repo-relative, like `in:`), the way
`AGENTS.md` conventions do:

```yaml
  - henxel: "None of the words in @banned-words.md are used"
    in: ./posts/*
    why: Tone is defined in @tone.md — read it before judging.
    make_sure_that: true
```

The referenced files are shown to the judge before the diff, with a line explaining what
`@banned-words.md` means, so the model reads the list, then the change. Quote a path with
spaces: `@"style notes/tone.md"`. Trailing punctuation is fine (`…in @banned-words.md.`).

- Files only, inside the repository. A reference that escapes the repo (`@../x.md`) is
  **refused** — the contract must work for anyone who clones it, and a stray path must
  never ship to a hosted judge. Share a list across repos by committing a copy.
- A missing file fails open ("could not be judged — @x not found"), like an unreachable
  judge: a typo never locks a commit.
- If the referenced file is itself staged, the judge sees the staged version.
- Editing the referenced file changes the question, so the cache is invalidated.
- Referenced files are protected from the `max_chars` budget: it's the diff that gets
  truncated, never the list.

When the list is literal and exact, a deterministic check is still cheaper and never
wrong; `@path` shines when the rule needs reading — inflections, paraphrase, a list with
nuance like "avoid unless quoting".

## The judge

Any **OpenAI-compatible chat endpoint** works — local or remote, with or without a key.
Henxels sends one `POST {base_url}/chat/completions` with the standard library only.

| key            | default                      | meaning                                                                  |
| -------------- | ---------------------------- | ------------------------------------------------------------------------ |
| `base_url`     | `http://localhost:11434/v1`  | endpoint root ending in `/v1` (Ollama's default)                          |
| `model`        | `qwen3:8b`                   | model id as the endpoint knows it                                        |
| `api_key_env`  | `OPENAI_API_KEY`             | env var holding the key — the key itself never goes in the YAML          |
| `timeout`      | `60`                         | seconds per verdict before failing open                                  |
| `max_chars`    | `60000`                      | diff budget per verdict; longer diffs are truncated with a note          |
| `extra_body`   | `{}`                         | merged into the request body, e.g. `{chat_template_kwargs: {enable_thinking: false}}` |
| `block_above`  | `0.8`                        | a `level: block` henxel blocks only at or above this confidence          |
| `warn_above`   | `0`                          | failures below this confidence are dropped                               |

`judge: true` takes every default (a local Ollama).

> **Your diff leaves the machine** if `base_url` points at a remote service. A staged diff
> can contain secrets and unreleased work. Prefer a local endpoint; if you use a hosted
> one, that's a conscious decision the committed `henxels.yaml` makes visible.

## What the judge sees

Only **change**. The evidence is a unified diff (HEAD → index) of the staged files in the
henxel's scope, plus a note for deletions. Consequences:

- `henxels check --all` skips these henxels — there is no change to judge.
- A commit that doesn't touch the scope costs **no tokens** and is never nagged.
- The judge is told to judge only what the diff shows, not to assume work elsewhere.

## Severity follows confidence

A judge is fallible, and a flaky gate teaches people to reach for `--no-verify`. So the
verdict's strength decides the finding's strength:

| verdict                                        | outcome                                                    |
| ---------------------------------------------- | ---------------------------------------------------------- |
| holds                                          | pass                                                       |
| does not hold, confidence ≥ `block_above`      | instruction at the henxel's `level`                         |
| does not hold, below `block_above`             | **warn**, whatever the level                               |
| does not hold, below `warn_above`              | dropped                                                    |
| does not hold, no confidence available         | taken at face value (henxel's `level`)                     |
| judge unreachable / garbage answer / no `judge:` | **warn** — "could not be judged", commit allowed         |

Confidence is read from the endpoint's **logprobs** on the decision token (P(false) vs
P(true)), which vLLM, llama.cpp, OpenAI and most compatible servers return; a server that
doesn't (some proxies) simply yields verdicts without confidence. Every failure also
carries the judge's **reason** — the actual instruction an agent can act on:

```text
✗ New CLI flags are documented in README.md
    README.md was not changed, but cli.py adds a --json flag — the judge is 96% sure
    this does not hold: New CLI flags are documented in README.md
```

The judge never blocks on its own outage. Infrastructure failure is a warning, never a
locked repository.

## Cost and caching

Verdicts are cached in the private git dir (`.git/henxels/judge-cache.json`) keyed by
model, endpoint, sentence, background and evidence, so a re-run of the hooks on the same
staged change asks nothing. Outages aren't cached. Requests use temperature 0.

## Choosing a model

Anything that follows instructions and emits JSON is enough — the task is "read this diff,
say true/false and why". A 4–8B instruct model on Ollama is fine for most repos; reasoning
models are slower for little gain here, so turn thinking off where the server allows it
(`extra_body`). Hosted frontier models are the most accurate and the most expensive way to
judge a commit; a warm local model is often the better trade.

## What it is not

- **Not a replacement for the deterministic statements.** If a glob or a frontmatter check
  can express the rule, use it — it's free, instant and never wrong. `make_sure_that` is
  for the rules those can't reach.
- **Not the only escape hatch.** Editing the contract still is. A judge's verdict is a
  test result, not a policy.
- **Not tied to one vendor.** The judge is a small interface (sentence + evidence →
  holds/confidence/reason). Today it's implemented over the OpenAI chat shape; a model that
  returns calibrated decisions directly could slot in later without a contract change.
