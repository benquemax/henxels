"""Security statements: keep things that must never be committed out of the repo.

``no_secrets`` is conservative on purpose — high-precision patterns over guesswork, so
it blocks real credentials without nagging on prose. As always, the escape hatch is the
contract: narrow the henxel's ``in:``/``except:`` if a match is a false positive.
"""

from __future__ import annotations

import re

from henxels.statements.registry import statement

_SECRET_PATTERNS = [
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    (
        "hardcoded credential",
        re.compile(r"""(?i)\b(?:api[_-]?key|secret|token|password|passwd)\b\s*[:=]\s*['"][^'"\s]{8,}['"]"""),
    ),
]


@statement("no_secrets", help="files contain no credentials (private keys, API tokens, passwords)", builtin=True)
def no_secrets(param, scope):
    if param is False:
        return []
    violations = []
    for f in scope.files:
        text = scope.read_text(f)
        if not text:
            continue
        for label, rx in _SECRET_PATTERNS:
            if rx.search(text):
                violations.append(f"{f} — looks like a {label}; secrets never belong in the repo (use a secret manager)")
                break
    return violations
