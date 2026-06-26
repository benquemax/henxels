"""Glob matching with sane ``**`` semantics, dependency-free.

We need globs that behave the way people expect in a structure contract:

* ``*``   matches within a single path segment (no ``/``)
* ``?``   matches a single non-``/`` character
* ``**``  matches across segments (any characters, including ``/``)
* ``**/`` matches *zero or more* leading directories, so ``**/*_test.py``
          matches both ``foo_test.py`` and ``a/b/foo_test.py``

``fnmatch`` and ``pathlib.match`` don't give us all of this, so we translate to a
regex once and cache it.
"""

from __future__ import annotations

import re
from functools import lru_cache


@lru_cache(maxsize=512)
def glob_to_regex(pattern: str) -> str:
    """Translate a glob ``pattern`` into an anchored regex string."""
    p = pattern.replace("\\", "/")
    out: list[str] = []
    i, n = 0, len(p)
    while i < n:
        c = p[i]
        if c == "*":
            if i + 1 < n and p[i + 1] == "*":
                # '**/' -> zero or more directories; bare '**' -> anything
                if i + 2 < n and p[i + 2] == "/":
                    out.append("(?:.*/)?")
                    i += 3
                else:
                    out.append(".*")
                    i += 2
            else:
                out.append("[^/]*")
                i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        elif c == "/":
            out.append("/")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return "^" + "".join(out) + "$"


def glob_match(pattern: str, path: str) -> bool:
    """Return True if ``path`` (posix-style) matches glob ``pattern``."""
    return re.match(glob_to_regex(pattern), str(path).replace("\\", "/")) is not None
