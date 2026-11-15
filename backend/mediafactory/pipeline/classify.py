"""Sensitive-content and rights checks for a finished script, reported as quality-check items.

The AI (task route "classify", or "script" when classify is not set up) reads the narration and flags
content that YouTube or Instagram may restrict. Horror itself is expected and fine. A failed check never
stops a video; it only means the video waits for a person instead of being published automatically.
"""

import logging

from sqlalchemy.orm import Session

from mediafactory.ai.jsonparse import extract_json
from mediafactory.ai.router import TaskNotConfigured, run_task

log = logging.getLogger(__name__)

FLAGS = ("minors_harm", "sexual", "self_harm", "hate", "dangerous", "graphic_gore", "real_tragedy")
ALWAYS_BLOCK = {"minors_harm", "sexual", "self_harm", "hate", "dangerous"}  # any mention -> needs a person
SEVERITIES = ("none", "low", "high")

SCHEMA = {
    "type": "object",
    "properties": {
        "flags": {"type": "array", "items": {"type": "string", "enum": list(FLAGS)}},
        "severity": {"type": "string", "enum": list(SEVERITIES)},
        "reason": {"type": "string"},
    },
    "required": ["flags", "severity", "reason"],
    "additionalProperties": False,
}

SYSTEM = """You check narration scripts for YouTube Shorts and Instagram Reels before they are published.
The channel tells fictional horror and mystery stories: fear, ghosts, monsters, death and mild violence are
expected and are NOT a problem by themselves. Flag only what the platforms restrict or demonetise:
- minors_harm: a child is harmed, abused or sexualised
- sexual: explicit sexual content
- self_harm: suicide or self-harm described in detail or presented positively
- hate: hateful or demeaning content about a protected group
- dangerous: instructions that could cause real harm (weapons, drugs, dangerous challenges)
- graphic_gore: very explicit, lingering gore
- real_tragedy: a real, identifiable recent crime, disaster or real private person presented as entertainment
severity: none (nothing flagged), low (brief or mild), high (central to the story or explicit).
Return ONLY a JSON object: {"flags": [...], "severity": "none|low|high", "reason": "<one short sentence>"}"""


def classify_script(session: Session, narration: str, *, language: str) -> dict:
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Language: {language}\n\n{narration[:6000]}"}]  # fmt: skip
    try:
        try:
            result = run_task(session, "classify", messages, json_schema=SCHEMA, max_tokens=300, temperature=0.0)
        except TaskNotConfigured:
            result = run_task(session, "script", messages, json_schema=SCHEMA, max_tokens=300, temperature=0.0)
        data = extract_json(result.text)
        if not isinstance(data, dict) or "flags" not in data:
            raise ValueError(f"unreadable reply: {result.text[:100]}")
    except Exception as exc:  # noqa: BLE001 - the check must never stop a video
        log.warning("content check failed: %s", exc)
        return {"error": str(exc)[:200]}
    flags = [f for f in dict.fromkeys(str(x).strip().lower() for x in data.get("flags") or []) if f in FLAGS]
    severity = str(data.get("severity") or "none").strip().lower()
    severity = severity if severity in SEVERITIES else ("low" if flags else "none")
    return {"flags": flags, "severity": "none" if not flags else severity, "reason": str(data.get("reason") or "")[:200],
            "model": getattr(result, "model", None)}  # fmt: skip


def content_check(info: dict | None) -> dict:
    if not info or "error" in info:
        return {"name": "content", "ok": False, "value": "not checked (AI unavailable) — please review"}
    flags = info.get("flags") or []
    blocked = bool(set(flags) & ALWAYS_BLOCK) or (bool(flags) and info.get("severity") == "high")
    value = "nothing sensitive" if not flags else f"{', '.join(flags)} ({info.get('severity')})"
    if info.get("reason") and flags:
        value += f": {info['reason']}"
    return {"name": "content", "ok": not blocked, "value": value[:240], "flags": flags}


def rights_check(rights_status: str | None) -> dict:
    status = rights_status or "unknown"
    return {"name": "rights", "ok": status != "restricted", "value": status}


def with_checks(qc: dict, info: dict | None, rights_status: str | None) -> dict:
    checks = [content_check(info), rights_check(rights_status)]
    return {**qc, "passed": bool(qc.get("passed", True)) and all(c["ok"] for c in checks),
            "checks": [*qc.get("checks", []), *checks]}  # fmt: skip
