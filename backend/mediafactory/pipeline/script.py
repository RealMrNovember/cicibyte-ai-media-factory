"""Script stage: turn a source item into an ORIGINAL short-form script ('inspired' mode)."""

import json

from sqlalchemy.orm import Session

from mediafactory.ai.jsonparse import extract_json
from mediafactory.ai.router import run_task
from mediafactory.db.models import SourceItem

WORDS_PER_SECOND = 2.5  # ~150 wpm narration
LANGUAGE_NAMES = {"en": "English", "tr": "Turkish"}

SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "hook": {"type": "string"},
        "narration": {"type": "string"},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "hook", "narration", "description", "tags"],
    "additionalProperties": False,
}

SYSTEM = """You write narration scripts for vertical YouTube Shorts (horror / mystery stories).
Rules:
- Write an ORIGINAL story. Use the source only for its idea, theme and atmosphere. Never copy sentences,
  names or distinctive details from it. Change characters, place and twist.
- Write entirely in {language}. Natural spoken {language}, first person, present tense, short sentences.
- The first sentence is the hook: it must create instant curiosity or dread.
- Build tension, end with a chilling twist, then one short line inviting viewers to follow for more.
- No stage directions, no emojis, no hashtags inside the narration, no headings.
- Length: about {words} words of narration (it will be read aloud in about {seconds} seconds).
Return ONLY a JSON object with keys: title (max 80 chars, intriguing, no clickbait lies), hook (the first
sentence), narration (the full text to read aloud, starting with the hook), description (2-3 sentences for
YouTube), tags (5-10 short tags)."""


def build_messages(item: SourceItem, language: str, seconds: int) -> list[dict]:
    words = int(seconds * WORDS_PER_SECOND)
    source = (item.normalized_text or "")[:6000]
    return [
        {"role": "system", "content": SYSTEM.format(language=LANGUAGE_NAMES.get(language, language), words=words,
                                                   seconds=seconds)},  # fmt: skip
        {"role": "user", "content": f"Source idea (do not copy):\nTITLE: {item.title}\n\n{source}"},
    ]


def generate_script(session: Session, item: SourceItem, *, language: str = "en", seconds: int = 50) -> dict:
    result = run_task(session, "script", build_messages(item, language, seconds), json_schema=SCHEMA, max_tokens=3000)
    data = extract_json(result.text)
    if not isinstance(data, dict) or not str(data.get("narration", "")).strip():
        raise ValueError(f"script model returned no narration: {json.dumps(data)[:200]}")
    data["tags"] = [str(t).strip().lstrip("#") for t in data.get("tags") or [] if str(t).strip()][:10]
    data["title"] = str(data.get("title") or item.title)[:100]
    data["model"], data["provider_id"] = result.model, result.provider_id
    return data
