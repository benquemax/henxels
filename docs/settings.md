---
title: Settings
summary: The settings block holds behaviours — staging, push, and delete protections plus similarity and large-file warnings and the judge for natural-language rules — the parts of the contract that aren't tests.
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

## judge

The language model that judges [natural-language henxels](natural-language-henxels.md)
(`make_sure_that`). Any OpenAI-compatible chat endpoint — local (Ollama, llama.cpp, vLLM,
LM Studio) or hosted — with or without a key:

```yaml
settings:
  judge:
    base_url: http://localhost:11434/v1   # default: Ollama
    model: qwen3:8b
    api_key_env: OPENAI_API_KEY           # the env var, never the key itself
    timeout: 60
    extra_body: {chat_template_kwargs: {enable_thinking: false}}   # optional passthrough
    block_above: 0.8                      # block only when the judge is at least this sure
    fallbacks:                            # tried in order when the primary fails
      - base_url: https://api.openai.com/v1
        model: gpt-4o-mini
        api_key_env: OPENAI_API_KEY
```

`judge: true` takes the defaults. Without a `judge:` block, a `make_sure_that` henxel only
warns that no judge is configured.

**Keep the endpoint out of the contract.** `henxels.yaml` is committed and should be true
for everyone who clones it; a hostname on your LAN is not a rule of the project. The
contract says *that* there is a judge; the machine says *where*, through the environment:

| Variable                    | Overrides    |
|-----------------------------|--------------|
| `HENXELS_JUDGE_URL`         | `base_url`   |
| `HENXELS_JUDGE_MODEL`       | `model`      |
| `HENXELS_JUDGE_TIMEOUT`     | `timeout`    |
| `HENXELS_JUDGE_EXTRA_BODY`  | `extra_body` (JSON, merged over the contract's) |
| `HENXELS_JUDGE_FALLBACKS`   | `fallbacks` (JSON array, appended to the contract's list) |

So the committed contract can be just `judge: true` (or `judge: {api_key_env: MY_KEY}`),
and your shell profile carries `HENXELS_JUDGE_URL=http://my-box:4800/v1`. A clone without
those variables falls back to the contract's values, then the defaults — and if nothing
answers there, it warns "could not be judged" and moves on. The environment never switches
judging *on*: without a `judge:` key in the contract the variables are ignored. The full
key table and the confidence rules are in the [guide](natural-language-henxels.md).

**Fallback judges.** When the primary endpoint fails (transport error, HTTP error, bad
response), each entry in `fallbacks:` is tried in order. Only infrastructure failures
trigger fallback — a real verdict from the primary stops the chain. Each fallback supports
`base_url`, `model`, `api_key_env`, `timeout`, `max_chars`, and `extra_body`; policy
settings (`block_above`, `warn_above`) are shared. See the
[guide](natural-language-henxels.md#fallback-judges) for details.

## Where settings are read

Behaviours run during `henxels check` and inside the git hooks. They are not statements, so
they never appear in the `henxels:` list — and a custom statement that uses a settings name
is flagged (see [Custom checks](custom-checks.md)).
