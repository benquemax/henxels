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
| `kind`         | `openai`                     | `openai` (a chat model) or `systemone` (a [decision model](#decision-models-kind-systemone)) |
| `base_url`     | `http://localhost:11434/v1`  | endpoint root ending in `/v1` (Ollama's default); for `systemone` the server root, default `http://localhost:11434` |
| `model`        | `qwen3:8b`                   | model id as the endpoint knows it; for `systemone` the default is `nimble` |
| `api_key_env`  | `OPENAI_API_KEY`             | env var holding the key — the key itself never goes in the YAML          |
| `timeout`      | `60`                         | seconds per verdict before failing open                                  |
| `max_chars`    | `60000`                      | diff budget per verdict; longer diffs are truncated with a note          |
| `extra_body`   | `{}`                         | merged into the request body, e.g. `{chat_template_kwargs: {enable_thinking: false}}` |
| `block_above`  | `0.8`                        | a `level: block` henxel blocks only at or above this confidence          |
| `warn_above`   | `0`                          | failures below this confidence are dropped                               |

`judge: true` takes every default (a local Ollama).

Every "where" key has an environment override — `HENXELS_JUDGE_KIND`, `_URL`, `_MODEL`, `_TIMEOUT`,
`_EXTRA_BODY` (JSON) — that wins over the contract, so a LAN hostname or a model id never
has to be committed; see [settings](settings.md#judge). The contract decides *that* there
is a judge, the machine decides *where*.

> **Your diff leaves the machine** if `base_url` points at a remote service. A staged diff
> can contain secrets and unreleased work. Prefer a local endpoint; if you use a hosted
> one, that's a conscious decision the committed `henxels.yaml` makes visible.

### Decision models (`kind: systemone`)

A *decision model* doesn't chat: it reads a text and answers named questions with
probabilities. Ollama (0.35+) serves them on the **System One** API, and hosted providers
(TypeSafe, AWS, Upstage) speak the same wire format. With `kind: systemone` the statement
becomes one yes/no question, sent as `POST {base_url}/v1/systemone`:

```yaml
settings:
  judge:
    kind: systemone
    model: nimble                 # any decision model: `ollama pull nimble`
    # base_url: http://localhost:11434   (the server root — default; a trailing /v1 is tolerated)
    # api_key_env: TYPESAFE_API_KEY      (hosted providers; sent as a Bearer token)
```

The answer is P(yes), so every verdict carries a **calibrated confidence** without any
logprobs support — `block_above` works out of the box. The trade-off: a decision model
gives **no reason**, so a failure says only how sure it is
("the judge is 93% sure this does not hold: …"), not what to change. A model that can't
answer System One (a chat model, say) is refused by the server and fails open like any
other outage — which is what a `fallbacks:` entry of the other kind is for:

```yaml
    fallbacks:
      - kind: openai
        base_url: https://api.openai.com/v1
        model: gpt-4o-mini
```

Decision models only read, never write, so they are fast where it matters for a gate:
the whole diff is one forward pass. They still have a context window — keep `max_chars`
within it: the default 60,000 characters is about 15k tokens, so lower `max_chars` for a
model with a smaller window. A local model's first call of the day also pays for loading
it (a minute or more for a large one), so raise `timeout` above the default 60 seconds, or a
cold start only warns "could not be judged".

They also don't reason before answering, so they are **less reliable than a chat judge on
rules that need inference** from a diff. In our live runs a 27B decision model blocked an
undocumented CLI flag, but let through modules whose diffs showed no docstring (it
answered "holds" at 64%). Use them for rules the diff shows plainly, keep `block_above`
at its default so a coin-flip answer only warns, and prefer a chat judge for subtle ones.

### Fallback judges

A local model can be down, a hosted API can timeout. Rather than failing open every time,
you can list **fallback** endpoints that are tried in order when the primary fails:

```yaml
settings:
  judge:
    base_url: http://localhost:11434/v1   # primary: local Ollama
    model: qwen3:8b
    fallbacks:
      - base_url: https://api.openai.com/v1   # first backup
        model: gpt-4o-mini
        api_key_env: OPENAI_API_KEY
      - base_url: https://openrouter.ai/api/v1  # second backup
        model: meta-llama/llama-3-8b-instruct
        api_key_env: OPENROUTER_API_KEY
```

Each fallback entry supports `kind`, `base_url`, `model`, `api_key_env`, `timeout`, `max_chars`,
and `extra_body`. Policy settings (`block_above`, `warn_above`) stay on the primary — they
govern what to do with a verdict, not how to reach the judge.

**Only infrastructure failures trigger fallback.** A confident "does not hold" from the
primary is a real answer — falling back would let a failing check pass by shopping for a
more lenient model. Transport errors, HTTP errors, bad JSON, and refused requests all count
as failures; a parseable verdict does not.

`HENXELS_JUDGE_FALLBACKS` (a JSON array) appends additional fallbacks from the environment,
so a developer can add a personal backup without editing the committed contract.

## What the judge sees

By default, only **change**. The evidence is a unified diff (HEAD → index) of the staged
files in the henxel's scope, plus a note for deletions. Consequences:

- `henxels check --all` skips these henxels — there is no change to judge.
- A commit that doesn't touch the scope costs **no tokens** and is never nagged.
- The judge is told to judge only what the diff shows, not to assume work elsewhere.

### Corpus-wide rules with `evidence: full`

Diff-only mode structurally cannot verify properties across the entire corpus — if you
have 14 chapters and only change one, the judge only sees that one chapter's diff. For
rules like "all chapters follow convention X", use the mapping form with `evidence: full`:

```yaml
henxels:
  - henxel: "All chapters follow the style guide"
    in: ./chapters/*
    make_sure_that:
      text: "Every chapter uses consistent heading levels and tone"
      evidence: full
```

With `evidence: full`, the judge sees the **complete content** of every file in scope,
not just diffs. This works even without staged changes (`check --all` included), making
`make_sure_that` a corpus gate, not just a diff gate. The tradeoff is cost: every file
in scope is sent on every check, so keep the scope tight and the model cheap.

The dict form also accepts `sentences:` (a list) instead of `text:` for multiple
sentences, and `evidence:` defaults to `diff` when omitted.

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

## Large diffs: automatic chunking

When the evidence exceeds `max_chars` (default 60,000 characters), it is automatically
split into multiple requests — one per chunk. Chunks are split on **file boundaries**:
each file's diff or content is an atomic unit and is never split mid-file. If a single
file exceeds the budget, it is sent alone (the judge truncates at prompt level).

The verdicts are aggregated: if **any** chunk says "does not hold", the overall result
fails. All chunks must say "holds" for the rule to pass. Each chunk is cached
independently, so a re-run only re-asks for chunks whose evidence changed.

This means huge diffs (refactors, bulk renames, generated files) are handled correctly
instead of being silently truncated. The tradeoff is cost: more chunks = more API calls.
Keep `max_chars` high enough to fit most commits in one chunk; lower it only when your
endpoint has a hard context limit.

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
  holds/confidence/reason), implemented over the OpenAI chat shape and the System One
  decision API; another backend slots in as another `kind` without a contract change.
