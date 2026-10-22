"""Security statements: keep things that must never be committed out of the repo.

``no_secrets`` is conservative on purpose — high-precision patterns over guesswork, so
it blocks real credentials without nagging on prose. As always, the escape hatch is the
contract: narrow the henxel's ``in:``/``except:`` if a match is a false positive. A repo
whose own token shape is not covered passes a list of extra regexes instead of ``true``.
"""

from __future__ import annotations

import re

from henxels.statements.registry import statement

_SECRET_PATTERNS = [
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    # Google Cloud API key (Gemini, Maps, Firebase/Identity Platform all share the shape).
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    (
        "hardcoded credential",
        # A quoted value with placeholder marks (<…>, ${…}, {…}, a trailing "...") is a
        # doc example, not a credential — docs are full of TOKEN="<paste here>".
        re.compile(
            r"""(?i)\b(?:api[_-]?key|secret|token|password|passwd)\b\s*[:=]\s*"""
            r"""['"](?![^'"\s]*(?:[<>{}$]|\.\.\.))[^'"\s]{8,}['"]"""
        ),
    ),
]


@statement(
    "no_secrets",
    help="files contain no credentials (private keys, API tokens, passwords); a list adds repo-specific regexes",
    builtin=True,
)
def no_secrets(param, scope):
    if param is False:
        return []
    patterns = list(_SECRET_PATTERNS)
    if isinstance(param, list):
        patterns += [("repo-specific secret", re.compile(p)) for p in param]
    violations = []
    for f in scope.files:
        text = scope.read_text(f)
        if not text:
            continue
        for label, rx in patterns:
            if rx.search(text):
                violations.append(f"{f} — looks like a {label}; secrets never belong in the repo (use a secret manager)")
                break
    return violations
