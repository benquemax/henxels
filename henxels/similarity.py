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
from collections import Counter
from pathlib import Path

from henxels.engine import gitinfo
from henxels.findings import WARN, Finding
from henxels.util.glob import glob_match

MAX_BYTES = 200_000  # skip very large files; they aren't the scatter this guards against


def find_duplicates(
    root: Path | str,
    candidates: list[str],
    threshold: float = 0.85,
    excludes: tuple[str, ...] | list[str] = (),
    corpus: list[str] | None = None,
    deep: bool = True,
) -> list[tuple[str, str, float]]:
    """Return (candidate, most_similar_committed_file, ratio) above ``threshold``.

    ``deep=True`` diffs every candidate against the whole corpus — for
    changed-file scans. ``deep=False`` diffs only pairs sharing whole lines —
    for whole-repo scans, where all-pairs diffing is O(N²) minutes.
    """
    root = Path(root)
    if corpus is None:
        corpus = gitinfo.tracked_files(root)

    files: dict[str, tuple[Counter, int, str]] = {}  # path -> (line counts, chars, text)
    index: dict[str, list[str]] = {}  # stripped line -> corpus files containing it
    for path in corpus:
        if _excluded(path, excludes):
            continue
        lines = _lines(root, path)
        if not lines:
            continue
        counts = Counter(lines)
        files[path] = (counts, sum(len(li) for li in lines), "\n".join(lines))
        for line in counts:
            index.setdefault(line, []).append(path)

    results: list[tuple[str, str, float]] = []
    for cand in candidates:
        if _excluded(cand, excludes):
            continue
        if cand in files:
            ccounts, cweight, cnorm = files[cand]
        else:
            lines = _lines(root, cand)
            if not lines:
                continue
            ccounts, cweight, cnorm = Counter(lines), sum(len(li) for li in lines), "\n".join(lines)

        if deep:
            pool = ((other, item) for other, item in files.items() if other != cand)
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
                (other, files[other])
                for other, matched in shared.items()
                if 2.0 * matched / (cweight + files[other][1]) >= floor or files[other][2] == cnorm
            )

        clen = len(cnorm)
        best, best_ratio = None, 0.0
        matcher = difflib.SequenceMatcher()
        matcher.set_seq2(cnorm)
        for other, (_, _, otext) in pool:
            if otext == cnorm:
                ratio = 1.0
            else:
                if 2.0 * min(clen, len(otext)) / (clen + len(otext)) < threshold:
                    continue  # lengths alone rule the pair out
                matcher.set_seq1(otext)
                if matcher.quick_ratio() < threshold:
                    continue
                ratio = matcher.ratio()
            if ratio > best_ratio:
                best, best_ratio = other, ratio
        if best is not None and best_ratio >= threshold:
            results.append((cand, best, best_ratio))
    return results


DEFAULT_AT_MOST = 20  # a bulk import must not bury the commit output


def warn_similar(
    sim: dict | None, root: Path | str, candidates: list[str], deep: bool = True
) -> list[Finding]:
    """Settings-driven duplication warnings (v2).

    ``sim`` = {'above', 'ignore', 'at_most'} or None. Awareness needs a handful
    of examples, not a transcript: past ``at_most`` pairs we print a count
    instead, so importing an archive stays readable.
    """
    if not sim:
        return []
    threshold = float(sim.get("above", 0.85))
    excludes = sim.get("ignore", []) or []
    at_most = int(sim.get("at_most", DEFAULT_AT_MOST))
    findings: list[Finding] = []
    pairs = find_duplicates(root, candidates, threshold, excludes, deep=deep)
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
