"""Script Doctor: the AI grades its own script and, when the grade is low, rewrites it once with the notes.

Best effort only: if the review or the rewrite fails, the first draft is used as it is.
"""

import json
import logging

from sqlalchemy.orm import Session

from mediafactory.ai.jsonparse import extract_json
from mediafactory.ai.router import run_task
from mediafactory.pipeline.script import LANGUAGE_NAMES, WORDS_PER_SECOND

log = logging.getLogger(__name__)

PASS_SCORE = 7  # 1-10; below this the script is rewritten once
MIN_LENGTH, MAX_LENGTH = 0.7, 1.4  # allowed narration length, as a share of the target word count

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {"score": {"type": "integer"}, "problems": {"type": "array", "items": {"type": "string"}}},
    "required": ["score", "problems"],
    "additionalProperties": False,
}

REVIEW_SYSTEM = """You are a strict script editor reviewing narration for a vertical YouTube Short (horror / mystery).
Grade it from 1 to 10 on these points together:
- Hook: does the first sentence create instant curiosity or dread?
- Tension: does every sentence move the story forward, with no filler or repetition?
- Twist: is the ending surprising, chilling and earned?
- Spoken {language}: is it natural, correct, first person and easy to read aloud? Any words in another language?
- Rules: no stage directions, emojis, hashtags or headings in the narration; it ends with a short follow invite.
Score 9-10 only for scripts you would publish unchanged. List the concrete problems (at most 5, short, actionable).
Return ONLY a JSON object: {{"score": <1-10>, "problems": ["...", ...]}}"""

REWRITE = """An editor reviewed your script and gave it {score}/10. Problems to fix:
{problems}

Your script was:
TITLE: {title}
{narration}

Rewrite the whole script fixing every problem. Keep the same rules, language and length (about {words} words).
Return ONLY the JSON object with the same keys as before."""


def parse_review(text: str) -> tuple[int, list[str]]:
    data = extract_json(text)
    if not isinstance(data, dict) or "score" not in data:
        raise ValueError(f"unreadable review: {text[:120]}")
    score = max(1, min(10, int(data["score"])))
    return score, [str(p).strip() for p in data.get("problems") or [] if str(p).strip()][:5]


def length_problem(narration: str, seconds: int) -> str | None:
    target, count = int(seconds * WORDS_PER_SECOND), len(narration.split())
    if count < target * MIN_LENGTH:
        return f"too short: {count} words, it needs about {target}"
    if count > target * MAX_LENGTH:
        return f"too long: {count} words, it needs about {target}"
    return None


def review(session: Session, data: dict, language: str, seconds: int) -> tuple[int, list[str]]:
    system = REVIEW_SYSTEM.format(language=LANGUAGE_NAMES.get(language, language))
    user = f"TITLE: {data.get('title', '')}\n\n{data['narration']}"
    result = run_task(session, "script", [{"role": "system", "content": system}, {"role": "user", "content": user}],
                      json_schema=REVIEW_SCHEMA, max_tokens=600, temperature=0.2)  # fmt: skip
    score, problems = parse_review(result.text)
    if issue := length_problem(data["narration"], seconds):  # the model is bad at counting, so check it here
        score, problems = min(score, PASS_SCORE - 2), [issue, *problems]
    return score, problems


def treat(session: Session, messages: list[dict], data: dict, *, language: str, seconds: int, write) -> dict:
    """Review `data`; if it scores under PASS_SCORE, rewrite once with `write(messages)` and keep the better one."""
    try:
        score, problems = review(session, data, language, seconds)
    except Exception as exc:  # noqa: BLE001 - the doctor must never stop a video
        log.warning("script review failed: %s", exc)
        return {**data, "doctor": {"error": str(exc)[:200]}}
    if score >= PASS_SCORE:
        return {**data, "doctor": {"score": score, "problems": problems, "revised": False}}
    note = REWRITE.format(score=score, problems="\n".join(f"- {p}" for p in problems) or "- make it more gripping",
                          title=data.get("title", ""), narration=data["narration"],
                          words=int(seconds * WORDS_PER_SECOND))  # fmt: skip
    kept = {**data, "doctor": {"score": score, "problems": problems, "revised": False}}
    try:
        better = write([*messages, {"role": "user", "content": note}])
        new_score, new_problems = review(session, better, language, seconds)
    except Exception as exc:  # noqa: BLE001
        log.warning("script rewrite failed: %s", exc)
        return kept
    if new_score <= score:
        return kept
    return {**better, "doctor": {"score": new_score, "problems": new_problems, "revised": True, "first_score": score}}


def summary(info: dict | None) -> str:
    if not info:
        return ""
    if "error" in info:
        return "review skipped"
    text = f"score {info['score']}/10" + (f" (rewritten from {info['first_score']})" if info.get("revised") else "")
    return text + (f"; notes: {json.dumps(info['problems'][:2], ensure_ascii=False)}" if info.get("problems") else "")
