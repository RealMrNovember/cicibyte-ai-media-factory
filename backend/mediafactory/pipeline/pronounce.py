"""Pronunciation dictionary: words the voice reads wrongly are spelled the way they should sound.

Only the text sent to the voice changes; captions, titles and descriptions keep the original spelling.
A rule matches whole words (or phrases), ignoring case, and keeps what follows (e.g. Turkish suffixes after
an apostrophe: "YouTube'da" -> "Yu tüb'da").
"""

from sqlalchemy.orm import Session

from mediafactory.db.models import SystemSetting

KEY = "pronunciations"
MAX_RULES = 500
LANGS = ("any", "en", "tr")


def clean(items: list[dict]) -> list[dict]:
    out, seen = [], set()
    for it in items:
        word, say = str(it.get("word") or "").strip(), str(it.get("say") or "").strip()
        lang = it.get("language") or "any"
        if not word or not say or lang not in LANGS:
            continue
        key = (word.casefold(), lang)
        if key in seen:
            continue
        seen.add(key)
        out.append({"word": word[:80], "say": say[:120], "language": lang})
    return out


def rules(db: Session) -> list[dict]:
    row = db.get(SystemSetting, KEY)
    return clean(row.value) if row and isinstance(row.value, list) else []


def save(db: Session, items: list[dict]) -> list[dict]:
    value = clean(items)
    row = db.get(SystemSetting, KEY)
    if row is None:
        db.add(SystemSetting(key=KEY, value=value))
    else:
        row.value = value
    return value


def _fold(text: str, *, turkish: bool = True) -> str:
    # Character by character so the folded text keeps the same length (positions map back to the original).
    table = {"İ": "i", "I": "ı"} if turkish else {"İ": "i", "I": "i", "ı": "i"}
    return "".join(table.get(c) or (c.casefold() if len(c.casefold()) == 1 else c.lower()[:1]) for c in text)


def apply(text: str, items: list[dict], language: str) -> str:
    """Replace every rule for this language (longest phrases first) as a whole word, ignoring case."""
    active = sorted((r for r in items if r["language"] in ("any", language)), key=lambda r: -len(r["word"]))
    if not active:
        return text
    # Two foldings: Turkish (I->ı, İ->i) and plain, so "ISTANBUL" and "CICIBYTE" both match their rules.
    texts = (_fold(text), _fold(text, turkish=False))
    words = [(_fold(r["word"]), _fold(r["word"], turkish=False)) for r in active]
    out, i = [], 0
    while i < len(text):
        for r, ws in zip(active, words, strict=True):
            end = i + len(ws[0])
            before_ok = i == 0 or not text[i - 1].isalnum()
            after_ok = end >= len(text) or not text[end].isalnum() or not r["word"][-1].isalnum()
            if before_ok and after_ok and any(t.startswith(w, i) for t, w in zip(texts, ws, strict=True)):
                out.append(r["say"])
                i = end
                break
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def spoken(db: Session, text: str, language: str) -> str:
    return apply(text, rules(db), language)

