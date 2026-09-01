"""Duplication awareness — warn before a copy diverges.

Per the contract's intent: compare a file against the **committed** corpus only,
skip files that are similar *by purpose* (name-glob excludes), and surface matches
as **warnings**, never blocks. Awareness is the point — the agent reuses the
original instead of spawning a second, soon-to-diverge copy.

Two scan depths, chosen by the caller — never guessed:

- **deep** (changed-file scans: pre-commit, explicit paths): every candidate is
  difflib-compared against the whole committed corpus. Catches even a doc
  re-written from scratch about the same thing — same vocabulary, no shared
  lines. Cost is proportional to the *changed* files, so it stays cheap.
- **fast** (whole-repo scans: ``check --all``, the push gate): like git's own
  rename/copy detection, an inverted index (stripped line → files) shortlists
  only pairs sharing whole lines, and difflib scores just that shortlist.
  Near-linear instead of O(N²) pairwise diffing, with one deliberate blind
  spot: pairs sharing (almost) no whole lines are never diffed. Deep already
  warned about those when they were committed.
"""

from __future__ import annotations

import difflib
import time
from collections import Counter
from pathlib import Path

from henxels.engine import gitinfo
from henxels.findings import WARN, Finding
from henxels.util.glob import glob_match

MAX_BYTES = 200_000  # skip very large files; they aren't the scatter this guards against


class SimilarityResults(list):
    """The (candidate, match, ratio) list; ``truncated`` means the budget ran out."""

    truncated: bool = False


def find_duplicates(
    root: Path | str,
    candidates: list[str],
    threshold: float = 0.85,
    excludes: tuple[str, ...] | list[str] = (),
    corpus: list[str] | None = None,
    deep: bool = True,
    budget_seconds: float | None = None,
) -> SimilarityResults:
    """Return (candidate, similar_committed_file, ratio) pairs above ``threshold``.

    ``deep=True`` considers every candidate × corpus pair — for changed-file
    scans. ``deep=False`` considers only pairs sharing whole lines — for
    whole-repo scans, where all-pairs consideration is O(N²) minutes.

    A warning needs *a* match, not the closest one: each candidate's pairs are
    tried most-promising-first (character-frequency bound, descending) and the
    scan stops at the first full-diff hit. ``budget_seconds`` optionally caps
    the whole scan by wall clock; results are then partial and marked
    ``truncated``. Default: no cap — the scan always completes.
    """
    root = Path(root)
    if corpus is None:
        corpus = gitinfo.tracked_files(root)

    # path -> (line counts, char weight, normalized text, char counts)
    files: dict[str, tuple[Counter, int, str, Counter]] = {}
    index: dict[str, list[str]] = {}  # stripped line -> corpus files containing it
    for path in corpus:
        if _excluded(path, excludes):
            continue
        lines = _lines(root, path)
        if not lines:
            continue
        counts = Counter(lines)
        text = "\n".join(lines)
        files[path] = (counts, sum(len(li) for li in lines), text, Counter(text))
        for line in counts:
            index.setdefault(line, []).append(path)

    deadline = None if budget_seconds is None else time.monotonic() + budget_seconds
    results = SimilarityResults()
    for cand in candidates:
        if deadline is not None and time.monotonic() >= deadline:
            results.truncated = True
            break
        if _excluded(cand, excludes):
            continue
        if cand in files:
            ccounts, cweight, cnorm, cchars = files[cand]
        else:
            lines = _lines(root, cand)
            if not lines:
                continue
            text = "\n".join(lines)
            ccounts, cweight, cnorm, cchars = Counter(lines), sum(len(li) for li in lines), text, Counter(text)

        if deep:
            pool = (other for other in files if other != cand)
        else:
            # Shortlist via the inverted index: only corpus files sharing at
            # least one whole line with the candidate, floor-filtered so pairs
            # sharing only boilerplate lines (`---`) skip the expensive diff.
            # ponytail: threshold/3 floor is a heuristic — a pair with >~2/3 of
            # its line-weight differing is invisible here; deep scans aren't.
            shared: dict[str, int] = {}
            for line, n in ccounts.items():
                for other in index.get(line, ()):
                    if other != cand:
                        shared[other] = shared.get(other, 0) + min(n, files[other][0][line]) * len(line)
            floor = threshold / 3
            pool = (
                other
                for other, matched in shared.items()
                if 2.0 * matched / (cweight + files[other][1]) >= floor or files[other][2] == cnorm
            )

        # Rank the pool by an upper bound on the diff ratio (both bounds are
        # cheap: O(1) on lengths, then O(alphabet) on precomputed char counts),
        # so the likeliest duplicate is diffed first and one hit ends the scan.
        clen = len(cnorm)
        ranked: list[tuple[float, str]] = []
        for other in pool:
            otext = files[other][2]
            if otext == cnorm:
                ranked.append((2.0, other))  # identical — above any bound
                continue
            olen = len(otext)
            if 2.0 * min(clen, olen) / (clen + olen) < threshold:
                continue  # lengths alone rule the pair out
            bound = _quick_ratio(cchars, clen, files[other][3], olen)
            if bound >= threshold:
                ranked.append((bound, other))
        ranked.sort(reverse=True)

        matcher = difflib.SequenceMatcher()
        matcher.set_seq2(cnorm)
        for bound, other in ranked:
            if deadline is not None and time.monotonic() >= deadline:
                results.truncated = True
                break
            ratio = 1.0 if bound > 1.0 else _full_ratio(matcher, files[other][2])
            if ratio >= threshold:
                results.append((cand, other, ratio))
                break
    return results


def _quick_ratio(c1: Counter, l1: int, c2: Counter, l2: int) -> float:
    """difflib's quick_ratio upper bound, over precomputed character counts."""
    if len(c2) < len(c1):
        c1, c2 = c2, c1
    matches = sum(min(n, c2[ch]) for ch, n in c1.items())
    return 2.0 * matches / (l1 + l2)


def _full_ratio(matcher: difflib.SequenceMatcher, other_text: str) -> float:
    matcher.set_seq1(other_text)
    return matcher.ratio()


DEFAULT_AT_MOST = 20  # a bulk import must not bury the commit output


def warn_similar(
    sim: dict | None, root: Path | str, candidates: list[str], deep: bool = True
) -> list[Finding]:
    """Settings-driven duplication warnings (v2).

    ``sim`` = {'above', 'ignore', 'at_most', 'budget'} or None. Awareness needs
    a handful of examples, not a transcript: past ``at_most`` pairs we print a
    count instead, so importing an archive stays readable. When an explicit
    ``budget`` (seconds) runs out, the partial results are followed by one
    warning saying the scan is incomplete.
    """
    if not sim:
        return []
    threshold = float(sim.get("above", 0.85))
    excludes = sim.get("ignore", []) or []
    at_most = int(sim.get("at_most", DEFAULT_AT_MOST))
    budget = sim.get("budget")
    findings: list[Finding] = []
    pairs = find_duplicates(root, candidates, threshold, excludes, deep=deep, budget_seconds=budget)
    for cand, other, ratio in pairs[:at_most]:
        findings.append(
            Finding(
                level=WARN,
                henxel=f"Possible duplicate: {cand}",
                path=cand,
                message="",
                details=[f"~{round(ratio * 100)}% similar to {other} — reuse it, or confirm this copy is intentional"],
            )
        )
    if len(pairs) > at_most:
        findings.append(
            Finding(
                level=WARN,
                henxel="Possible duplicates (many)",
                path=pairs[at_most][0],
                message="",
                details=[
                    f"and {len(pairs) - at_most} more similar files not listed — "
                    "if this is a bulk import, exclude it via "
                    "settings.warn_about_similar_files.ignore"
                ],
            )
        )
    if pairs.truncated:
        findings.append(
            Finding(
                level=WARN,
                henxel="Similarity scan is partial",
                path="",
                message="",
                details=[
                    "the duplicate scan hit its warn_about_similar_files.budget, so some near-copies "
                    "may have gone unnoticed — raise the budget, or add generated/data paths to "
                    "warn_about_similar_files.ignore so the scan stays fast and complete"
                ],
            )
        )
    return findings


def _lines(root: Path, rel: str) -> list[str]:
    text = _read(root, rel)
    if text is None:
        return []
    return [line.strip() for line in text.splitlines() if line.strip()]


def _excluded(path: str, excludes) -> bool:
    return any(glob_match(pattern, path) for pattern in excludes)


def _read(root: Path, rel: str) -> str | None:
    p = root / rel
    try:
        if not p.is_file() or p.stat().st_size > MAX_BYTES:
            return None
        data = p.read_bytes()
    except OSError:
        return None
    if b"\x00" in data:  # binary
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None
