"""Link statements: keep a wiki of cross-linked markdown navigable.

Relative internal links are what survive a move, render in a web viewer, and let a
small model (or a graph-RAG indexer) walk page-to-page. These statements check that
internal links are relative, resolve to real files, that pages link outward, and that
every page is reachable from an index.
"""

from __future__ import annotations

import posixpath
import re

from henxels.statements.registry import statement

# [text](target) / ![alt](target) — capture the target.
_MD_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
_EXTERNAL = ("http://", "https://", "mailto:", "tel:", "//")


def _link_targets(text: str | None):
    for raw in _MD_LINK.findall(text or ""):
        t = raw.strip()
        if t:
            yield t.split()[0]  # drop a `(url "title")` suffix


def _internal_targets(text: str | None):
    """Targets that point inside the repo (skip external URLs and protocol-relative)."""
    for t in _link_targets(text):
        if not t.startswith(_EXTERNAL):
            yield t


@statement("links_are_relative", help="internal markdown links are relative, not absolute paths", builtin=True)
def links_are_relative(scope):
    violations = []
    for f in scope.files:
        if not f.endswith(".md"):
            continue
        for t in _internal_targets(scope.read_text(f)):
            if t.startswith("/"):
                violations.append(f"{f} — make this link relative (not an absolute path): {t}")
    return violations


@statement("links_resolve", help="every relative internal markdown link points at a real file", builtin=True)
def links_resolve(scope):
    violations = []
    for f in scope.files:
        if not f.endswith(".md"):
            continue
        base = posixpath.dirname(f)
        for t in _internal_targets(scope.read_text(f)):
            if t.startswith("/"):
                continue  # absolute is links_are_relative's concern
            target = t.split("#", 1)[0]  # drop a #anchor
            if not target:
                continue  # pure in-page anchor
            resolved = posixpath.normpath(posixpath.join(base, target))
            if not scope.exists(resolved):
                violations.append(f"{f} — dead link {t} → no file at {resolved}")
    return violations


@statement("min_outbound_links", help="each page links out to at least N other pages", builtin=True)
def min_outbound_links(param, scope):
    needed = int(param)
    violations = []
    for f in scope.files:
        if not f.endswith(".md"):
            continue
        targets = {t.split("#", 1)[0] for t in _internal_targets(scope.read_text(f))}
        targets.discard("")  # pure anchors don't count as outbound
        if len(targets) < needed:
            violations.append(f"{f} — has {len(targets)} outbound link(s); link to at least {needed} other page(s)")
    return violations


@statement("referenced_in", help="every page in scope is linked from this index file", builtin=True)
def referenced_in(param, scope):
    index = param if isinstance(param, str) else None
    if not index:
        return []
    text = scope.read_text(index)
    if text is None:
        return [f"create {index} and list every page in it"]
    base = posixpath.dirname(index)
    referenced = {
        posixpath.normpath(posixpath.join(base, t.split("#", 1)[0]))
        for t in _internal_targets(text)
        if t.split("#", 1)[0]
    }
    violations = []
    for f in scope.files:
        if not f.endswith(".md") or f == index:
            continue
        if f not in referenced:
            violations.append(f"{f} — add it to {index} under the right section")
    return violations
