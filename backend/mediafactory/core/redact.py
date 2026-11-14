"""Mask secrets before text reaches logs, audit records or error messages."""

import re

_MASK = "****"
_KEYS = r"(?:api[_-]?key|apikey|key|token|access_token|refresh_token|secret|client_secret|password|passwd)"

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(Bearer\s+)[A-Za-z0-9._~+/=-]+", re.IGNORECASE), r"\g<1>" + _MASK),
    (re.compile(r'("' + _KEYS + r'"\s*:\s*")[^"]*(")', re.IGNORECASE), r"\g<1>" + _MASK + r"\g<2>"),
    (re.compile(r"(?<![A-Za-z0-9_])(" + _KEYS + r"=)[^&\s\"']+", re.IGNORECASE), r"\g<1>" + _MASK),
]


def redact(text: str) -> str:
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text
