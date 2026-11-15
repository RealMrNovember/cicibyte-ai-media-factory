"""Originality check: how much of the narration is copied word for word from the source story.

Two signals, both on normalized words (lowercase, punctuation removed):
- overlap: share of the narration's 5-word sequences that also appear in the source;
- longest: the longest run of words copied in a row.
A script translated from the source cannot be caught this way (different words), only copied text.
"""

import re

N = 5
MAX_OVERLAP = 0.15  # more than 15% of 5-word sequences shared with the source
MAX_RUN = 12  # or 12+ words copied in a row
_WORD = re.compile(r"[^\W_]+(?:'[^\W_]+)?", re.UNICODE)


def words(text: str) -> list[str]:
    return _WORD.findall((text or "").casefold())


def _grams(ws: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(ws[i : i + n]) for i in range(len(ws) - n + 1)}


def longest_run(a: list[str], b: list[str]) -> int:
    """Length of the longest common run of words (dynamic programming, O(len(a)*len(b)) with one row)."""
    best, prev = 0, [0] * (len(b) + 1)
    for x in a:
        row = [0] * (len(b) + 1)
        for j, y in enumerate(b, 1):
            if x == y:
                row[j] = prev[j - 1] + 1
                best = max(best, row[j])
        prev = row
    return best


def check_originality(narration: str, source: str) -> dict:
    a, b = words(narration), words(source)
    if not b:
        return {"name": "originality", "ok": True, "value": "no source text"}
    grams = _grams(a, N)
    overlap = len(grams & _grams(b, N)) / len(grams) if grams else 0.0
    run = longest_run(a, b[:6000])
    ok = overlap <= MAX_OVERLAP and run < MAX_RUN
    return {"name": "originality", "ok": ok, "value": f"{overlap:.0%} shared phrases, {run} words in a row",
            "overlap": round(overlap, 3), "longest": run}  # fmt: skip


def with_originality(qc: dict, narration: str, source: str) -> dict:
    """Add the originality check to a QC result; a copied script fails QC, so it always waits for a person."""
    check = check_originality(narration, source)
    return {**qc, "passed": bool(qc.get("passed", True)) and check["ok"], "checks": [*qc.get("checks", []), check]}
