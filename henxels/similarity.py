"""Duplication awareness — warn before a copy diverges.

Per the contract's intent: compare a file against the **committed** corpus only,
skip files that are similar *by purpose* (name-glob excludes), and surface matches
as **warnings**, never blocks. Awareness is the point — the agent reuses the
original instead of spawning a second, soon-to-diverge copy.
"""

from __future__ import annotations

import difflib
from pathlib import Path

from henxels.engine import gitinfo
from henxels.findings import WARN, Finding
from henxels.util.glob import glob_match

MAX_BYTES = 200_000  # skip very large files; pairwise diffing them isn't worth it


def find_duplicates(
    root: Path | str,
    candidates: list[str],
    threshold: float = 0.85,
    excludes: tuple[str, ...] | list[str] = (),
    corpus: list[str] | None = None,
) -> list[tuple[str, str, float]]:
    """Return (candidate, most_similar_committed_file, ratio) above ``threshold``."""
    root = Path(root)
    if corpus is None:
        corpus = gitinfo.tracked_files(root)

    corpus_texts: dict[str, str] = {}
    for path in corpus:
        if _excluded(path, excludes):
            continue
        text = _read(root, path)
        if text is None:
            continue
        norm = _normalize(text)
        if norm:
            corpus_texts[path] = norm

    results: list[tuple[str, str, float]] = []
    for cand in candidates:
        if _excluded(cand, excludes):
            continue
        text = _read(root, cand)
        if text is None:
            continue
        cnorm = _normalize(text)
        if not cnorm:
            continue
        best, best_ratio = None, 0.0
        matcher = difflib.SequenceMatcher()
        matcher.set_seq2(cnorm)
        for other_path, otext in corpus_texts.items():
            if other_path == cand:
                continue
            matcher.set_seq1(otext)
            if matcher.quick_ratio() < threshold:
                continue
            ratio = matcher.ratio()
            if ratio > best_ratio:
                best, best_ratio = other_path, ratio
        if best is not None and best_ratio >= threshold:
            results.append((cand, best, best_ratio))
    return results


DEFAULT_AT_MOST = 20  # a bulk import must not bury the commit output


def warn_similar(sim: dict | None, root: Path | str, candidates: list[str]) -> list[Finding]:
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
    pairs = find_duplicates(root, candidates, threshold, excludes)
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


def _normalize(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


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
