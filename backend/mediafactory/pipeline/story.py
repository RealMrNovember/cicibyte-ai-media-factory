"""Write a brand-new story with the connected AI (for languages/topics with no good sources, e.g. Turkish)."""

import json

from sqlalchemy.orm import Session

from mediafactory.ai.jsonparse import extract_json
from mediafactory.ai.router import run_task
from mediafactory.pipeline.script import LANGUAGE_NAMES

SCHEMA = {
    "type": "object",
    "properties": {"title": {"type": "string"}, "story": {"type": "string"}},
    "required": ["title", "story"],
    "additionalProperties": False,
}

SYSTEM = """You are a horror and mystery fiction writer. Write a completely ORIGINAL short story.
- Write entirely in {language}, natural and fluent, as a first-person account told as if it really happened.
- Setting, names and details must fit the culture of {language} speakers.
- About {words} words. Build dread slowly and end with an unsettling twist.
- No headings, no emojis, no notes to the reader.
Return ONLY a JSON object: {{"title": "...", "story": "..."}}"""


def write_story(session: Session, topic: str, *, language: str = "tr", words: int = 600) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM.format(language=LANGUAGE_NAMES.get(language, language), words=words)},
        {"role": "user", "content": f"Topic / idea: {topic.strip() or 'surprise me'}"},
    ]
    # Plain JSON-in-prompt: some router models return empty content under strict json_schema for long text.
    result = run_task(session, "script", messages, max_tokens=8000)
    title, text = _parse(result.text)
    if len(text.split()) < 80:
        raise ValueError(f"the AI returned no usable story: {result.text[:200]}")
    return {"title": (title or topic)[:300], "story": text, "model": result.model}


def _parse(reply: str) -> tuple[str, str]:
    """(title, story). Models sometimes use another key, or answer in plain text: take the longest text then."""
    try:
        data = extract_json(reply)
    except (ValueError, json.JSONDecodeError):
        data = None
    if isinstance(data, dict):
        texts = [str(v).strip() for v in data.values() if isinstance(v, str)]
        story = str(data.get("story") or "").strip() or max(texts, key=lambda t: len(t.split()), default="")
        return str(data.get("title") or "").strip(), story
    return "", (reply or "").strip()
