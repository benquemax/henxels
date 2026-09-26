"""Judgement statements: natural-language henxels, verified by a language model.

``make_sure_that`` hands the henxel's own sentence (or its own sentences) plus evidence
to the configured judge (``settings.judge`` — any OpenAI-compatible endpoint) and turns
the verdict into instructions. By default the evidence is the **staged diff** (HEAD →
index) of files in scope — outside a staged context (``check --all``) there is nothing
to judge and it passes; when the scope wasn't touched, no tokens are spent.

With ``evidence: full`` (dict param form), the judge sees the **complete content** of
every file in scope, not just diffs. This enables corpus-wide rules ("all chapters
follow convention X") that diff-only mode structurally cannot verify. Full evidence
works even without a staged diff, making ``make_sure_that`` a corpus gate, not just a
diff gate.

A judge is fallible, so severity follows its confidence: a failure the judge is sure
about is a plain instruction (blocks if the henxel does); an unsure one — or a judge
that couldn't be reached — is an ``Advisory`` and only warns. Verdicts are cached per
evidence hash so a re-run of the hooks doesn't ask twice.

A sentence may point at a file with ``@path`` ("none of the words in @banned-words.md
are used"): the file — repo-relative, inside the repo — is read (staged version if it's
staged) and shown to the judge next to the diff. A missing reference fails open; one
that escapes the repository is refused, so a contract can never ship a stray file to a
hosted judge.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
from pathlib import Path

from henxels.findings import Advisory
from henxels.judge import JudgeConfig, OpenAICompatibleJudge, Verdict, config_from_settings
from henxels.statements.registry import as_list, statement

CACHE_FILE = "judge-cache.json"
CACHE_ENTRIES = 200


def make_judge(settings: dict):
    """The configured judge, or None when ``settings.judge`` is absent."""
    cfg = config_from_settings(settings)
    return None if cfg is None else OpenAICompatibleJudge(cfg)


def _parse_param(param, henxel):
    """Normalize the make_sure_that param into (sentences, why, evidence_mode).

    Accepted forms:
      - True / None     → ([henxel.text], henxel.why, "diff")
      - "string"        → (["string"], "", "diff")
      - ["a", "b"]      → (["a", "b"], "", "diff")
      - {text: "..."}   → (["..."], "", evidence or "diff")
      - {sentences: [...]} → ([...], "", evidence or "diff")
    """
    if isinstance(param, dict):
        evidence_mode = str(param.get("evidence", "diff")).lower()
        raw_sentences = param.get("sentences") or param.get("text")
        if raw_sentences is None:
            sentences = [henxel.text]
            why = henxel.why
        elif isinstance(raw_sentences, list):
            sentences = [str(s) for s in raw_sentences]
            why = ""
        else:
            sentences = [str(raw_sentences)]
            why = ""
        return sentences, why, evidence_mode
    if param is True or param is None:
        return [henxel.text], henxel.why, "diff"
    return [str(s) for s in as_list(param)], "", "diff"


@statement(
    "make_sure_that",
    help="a natural-language rule: the staged changes in scope are shown to a language model (settings.judge) which says whether the sentence holds",
    builtin=True,
)
def make_sure_that(param, henxel, scope, diff, settings):
    if param is False:
        return None

    sentences, why, evidence_mode = _parse_param(param, henxel)

    if evidence_mode == "full":
        blocks = build_full_evidence_blocks(scope.files, scope)
    else:
        if diff is None:
            return None
        blocks = build_evidence_blocks(scope.files, diff)
    if not blocks:
        return None  # nothing to judge — no tokens spent

    judge = make_judge(settings)
    if judge is None:
        return [Advisory(
            f"'{henxel.text}' is a natural-language henxel but no judge is configured — add a "
            f"`judge:` block under `settings:` in henxels.yaml (base_url, model, api_key_env)"
        )]

    cfg = config_from_settings(settings)
    chunks = chunk_evidence(blocks, cfg.max_chars)

    out: list[str] = []
    for sentence in sentences:
        references, problems = resolve_references(sentence + "\n" + why, scope, diff)
        if problems:
            out.extend(Advisory(f"'{sentence}' could not be judged — {p} (commit allowed; verify by hand)") for p in problems)
            continue
        # Judge each chunk and aggregate: any failure → overall failure
        worst: Verdict | None = None
        for chunk in chunks:
            v = _judge_cached(judge, cfg, scope.root, sentence, why, chunk, references)
            if v.holds is None:
                # Error verdict: keep going to try other chunks, but remember the error
                if worst is None or worst.holds is not None:
                    worst = v
            elif not v.holds:
                # Definite failure: stop early, this is the answer
                worst = v
                break
            else:
                # Holds: only record if we don't already have a failure
                if worst is None:
                    worst = v
        if worst is not None:
            instruction = _to_instruction(sentence, worst, cfg.block_above, cfg.warn_above)
            if instruction is not None:
                out.append(instruction)
    return out or None


# `@path` or `@"path with spaces"`; must start a word (so an e-mail address isn't one).
_REFERENCE = re.compile(r'(?<![\w.])@(?:"([^"]+)"|([^\s"\'`,;()\[\]]+))')


def find_references(text: str) -> list[str]:
    """The ``@path`` references in a sentence, normalized repo-relative, in order, unique."""
    out: list[str] = []
    for quoted, bare in _REFERENCE.findall(text):
        path = (quoted or bare).rstrip(".:!?")
        if path.startswith("./"):
            path = path[2:]
        if path and path not in out:
            out.append(path)
    return out


def resolve_references(text: str, scope, diff) -> tuple[dict[str, str], list[str]]:
    """Read every ``@path`` in ``text``. Returns ({name: content}, [problems])."""
    refs: dict[str, str] = {}
    problems: list[str] = []
    root = scope.root.resolve()
    for name in find_references(text):
        target = (root / name).resolve()
        if not _within(target, root):
            problems.append(f"@{name} points outside the repository — reference a committed copy instead")
            continue
        content = diff.new_text(name) if diff is not None and name in diff.changed else None
        if content is None:
            content = scope.read_text(name)
        if content is None or not target.is_file():
            problems.append(f"@{name} not found")
            continue
        refs[name] = content
    return refs, problems


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)  # is_relative_to needs 3.9+, but keep it explicit for readers
        return True
    except ValueError:
        return False


def build_evidence_blocks(files, diff) -> list[str]:
    """Per-file unified diff blocks (HEAD → index) of the staged files in scope.

    Returns a list of non-empty strings, one per changed/deleted file. Each block
    is an atomic unit for chunking — never split mid-file.
    """
    blocks: list[str] = []
    for f in sorted(files):
        if f in diff.deleted:
            blocks.append(f"--- a/{f}\n+++ /dev/null\n(file deleted)\n")
        elif f in diff.changed:
            block = _unified(f, diff.old_text(f), diff.new_text(f))
            if block:
                blocks.append(block)
    return blocks


def build_evidence(files, diff) -> str:
    """A unified diff (HEAD → index) of the staged files in scope; deletions listed."""
    return "\n".join(build_evidence_blocks(files, diff))


def build_full_evidence_blocks(files, scope) -> list[str]:
    """Per-file content blocks for every file in scope — a corpus gate, not a diff gate.

    Returns a list of strings, one per file. Each block includes the file path as a
    header and is an atomic unit for chunking.
    """
    from henxels.diffinfo import staged_diff

    diff = staged_diff(scope.root)
    blocks: list[str] = []
    for f in sorted(files):
        # Prefer the staged version (what would be committed); fall back to working tree
        content = None
        if diff is not None and f in diff.changed:
            content = diff.new_text(f)
        if content is None:
            content = scope.read_text(f)
        if content is not None:
            blocks.append(f"--- {f} ---\n{content.rstrip()}\n--- end of {f} ---")
    return blocks


def build_full_evidence(files, scope) -> str:
    """The complete content of every file in scope — a corpus gate, not a diff gate."""
    return "\n\n".join(build_full_evidence_blocks(files, scope))


def chunk_evidence(blocks: list[str], max_chars: int) -> list[str]:
    """Pack per-file evidence blocks into chunks that each fit within max_chars.

    Blocks are never split — each file's content is atomic. If a single block exceeds
    max_chars, it becomes its own chunk (the judge will truncate at prompt level).
    """
    if not blocks:
        return []
    chunks: list[str] = []
    current_parts: list[str] = []
    current_size = 0
    for block in blocks:
        block_size = len(block)
        # Separator cost: "\n\n" between blocks within a chunk
        sep_cost = 2 if current_parts else 0
        if current_parts and current_size + sep_cost + block_size > max_chars:
            # Flush current chunk
            chunks.append("\n\n".join(current_parts))
            current_parts = []
            current_size = 0
            sep_cost = 0
        current_parts.append(block)
        current_size += sep_cost + block_size
    if current_parts:
        chunks.append("\n\n".join(current_parts))
    return chunks


def _unified(rel: str, old: str | None, new: str | None) -> str:
    a = (old or "").splitlines(keepends=True)
    b = (new or "").splitlines(keepends=True)
    header_a = f"a/{rel}" if old is not None else "/dev/null"
    lines = list(difflib.unified_diff(a, b, fromfile=header_a, tofile=f"b/{rel}", n=3))
    if not lines:
        return ""
    return "".join(line if line.endswith("\n") else line + "\n" for line in lines)


def _to_instruction(sentence: str, v: Verdict, block_above: float, warn_above: float) -> str | None:
    if v.holds is None:
        detail = v.error or "unknown judge error"
        return Advisory(f"'{sentence}' could not be judged — {detail} (commit allowed; verify by hand)")
    if v.holds:
        return None
    reason = v.reason or "the judge says this does not hold"
    if v.confidence is None:
        return f"{reason} — the judge finds this does not hold: {sentence}"
    pct = f"{round(v.confidence * 100)}%"
    if v.confidence < warn_above:
        return None
    text = f"{reason} — the judge is {pct} sure this does not hold: {sentence}"
    return text if v.confidence >= block_above else Advisory(text)


# --- cache -------------------------------------------------------------------------


def _judge_cached(
    judge, cfg: JudgeConfig, root: Path, sentence: str, why: str, evidence: str, references: dict[str, str]
) -> Verdict:
    # The referenced files are part of the question: edit the list, get a fresh verdict.
    key = hashlib.sha256(
        json.dumps([cfg.model, cfg.base_url, sentence, why, evidence, references], sort_keys=True).encode()
    ).hexdigest()
    cache = _load_cache(root)
    hit = cache.get(key)
    if hit is not None:
        return Verdict(**hit)
    verdict = judge.judge(sentence, why, evidence, references)
    if verdict.holds is not None:  # never cache an outage
        cache[key] = {
            "holds": verdict.holds, "confidence": verdict.confidence, "reason": verdict.reason,
            "error": None, "model": verdict.model, "base_url": verdict.base_url,
        }
        _save_cache(root, cache)
    return verdict


def _cache_path(root: Path) -> Path:
    from henxels.engine.gitinfo import git_private_dir

    private = git_private_dir(root)
    return (private if private is not None else Path(root) / ".git") / "henxels" / CACHE_FILE


def _load_cache(root: Path) -> dict:
    try:
        data = json.loads(_cache_path(root).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_cache(root: Path, cache: dict) -> None:
    if len(cache) > CACHE_ENTRIES:
        cache = dict(list(cache.items())[-CACHE_ENTRIES:])
    path = _cache_path(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache), encoding="utf-8")
    except OSError:
        pass  # a cache that can't be written is just a cache
