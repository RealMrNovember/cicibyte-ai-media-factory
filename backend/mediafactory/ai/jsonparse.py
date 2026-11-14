# Adapted from purffle-shorts (MIT, Copyright (c) 2025 Purffle), commit 514fd2547227b98d951dfc1489fc8c7ce72f1b68
"""Pull a JSON value out of a model reply that may contain code fences, chatter or trailing commas."""

import json
import re
from typing import Any

_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)
_TRAILING_COMMA = re.compile(r",\s*([}\]])")


def _loads(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(_TRAILING_COMMA.sub(r"\1", text))


def extract_json(text: str) -> dict | list:
    candidates = [m.group(1) for m in _FENCE.finditer(text)] + [text.strip()]
    for cand in candidates:
        for opener, closer in (("{", "}"), ("[", "]")):
            start, end = cand.find(opener), cand.rfind(closer)
            if start == -1 or end <= start:
                continue
            try:
                value = _loads(cand[start : end + 1])
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict | list):
                return value
    raise ValueError(f"model reply contains no JSON: {text[:200]!r}")
