"""Export / import of all settings, so another computer or server can be set up in one step.

Plain settings (providers without keys, task routes, sources, schedules, YouTube client id, channel names) are
readable JSON. Secrets (API keys, client secrets, refresh tokens, Reddit secret) are only included when a
password is given, encrypted with a key derived from it (PBKDF2-SHA256 + Fernet), because the receiving
server has a different MF_SECRET_KEY. Import merges by name and never deletes anything.
"""

import base64
import json
import os
from datetime import UTC, datetime

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import select
from sqlalchemy.orm import Session

from mediafactory import __version__
from mediafactory.core.crypto import decrypt, encrypt
from mediafactory.db.models import AIProvider, AITaskRoute, Concept, Schedule, SourceConnector, YouTubeChannel
from mediafactory.sources.credentials import get_reddit_credentials, set_reddit_credentials

FORMAT = "cicibyte-mediafactory-settings"
ITERATIONS = 390_000


class PortabilityError(Exception):
    pass


def _fernet(password: str, salt: bytes) -> Fernet:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS)
    return Fernet(base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8"))))


def _safe_decrypt(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return decrypt(token)
    except Exception:
        return None


def export_settings(db: Session, *, password: str | None) -> dict:
    from mediafactory.youtube import oauth

    providers = list(db.scalars(select(AIProvider).order_by(AIProvider.id)))
    names = {p.id: p.name for p in providers}
    secrets: dict = {"providers": {}, "channels": {}}
    data = {
        "providers": [{"name": p.name, "kind": p.kind, "base_url": p.base_url, "locality": p.locality,
                       "timeout_s": p.timeout_s, "max_concurrency": p.max_concurrency, "enabled": p.enabled}
                      for p in providers],
        "routes": [{"task": r.task, "rounds": r.rounds, "retry_delay_s": r.retry_delay_s,
                    "steps": [{"provider": names.get(s.get("provider_id")), "model": s.get("model")} for s in r.steps or []]}
                   for r in db.scalars(select(AITaskRoute).order_by(AITaskRoute.task))],
        "sources": [{"name": c.name, "adapter": c.adapter, "params": c.params, "enabled": c.enabled,
                     "poll_interval_min": c.poll_interval_min, "default_rights": c.default_rights,
                     "default_language": c.default_language}
                    for c in db.scalars(select(SourceConnector).where(SourceConnector.deleted_at.is_(None)).order_by(SourceConnector.id))],
        "schedules": [{"name": s.name, "kind": s.kind, "enabled": s.enabled, "times": s.times, "weekdays": s.weekdays,
                       "timezone": s.timezone, "params": s.params} for s in db.scalars(select(Schedule).order_by(Schedule.id))],
        "concepts": [{"name": c.name, "enabled": c.enabled, "language": c.language, "topic": c.topic, "seconds": c.seconds,
                      "style": c.style, "voice": c.voice, "music": c.music, "background": c.background,
                      "youtube_channel": (db.get(YouTubeChannel, c.youtube_channel_id).channel_id
                                          if c.youtube_channel_id and db.get(YouTubeChannel, c.youtube_channel_id) else None),
                      "platforms": c.platforms, "privacy": c.privacy, "ready_buffer": c.ready_buffer,
                      "auto_approve": c.auto_approve} for c in db.scalars(select(Concept).order_by(Concept.id))],
        "youtube": {"client_id": (oauth.get_client(db) or {}).get("client_id"),
                    "channels": [{"channel_id": c.channel_id, "title": c.title, "thumbnail": c.thumbnail,
                                  "is_default": c.is_default} for c in db.scalars(select(YouTubeChannel))]},
    }  # fmt: skip
    for p in providers:
        if (key := _safe_decrypt(p.api_key_enc)) is not None:
            secrets["providers"][p.name] = key
    for c in db.scalars(select(YouTubeChannel)):
        if (tok := _safe_decrypt(c.refresh_token_enc)) is not None:
            secrets["channels"][c.channel_id] = tok
    client = oauth.get_client(db)
    if client:
        secrets["youtube_client_secret"] = client["client_secret"]
    reddit = get_reddit_credentials(db)
    if reddit:
        secrets["reddit"] = reddit
    from mediafactory.instagram.publish import get_account

    from mediafactory.pipeline.stock import coverr_key

    if ck := coverr_key(db):
        secrets["coverr_key"] = ck
    if (acc := get_account(db)) and (tok := _safe_decrypt(acc.get("token_enc"))) is not None:
        data["instagram"] = {k: acc.get(k) for k in ("user_id", "username", "account_type", "expires_at")}
        secrets["instagram_token"] = tok
    from mediafactory.tiktok import publish as ttp

    if app := ttp.get_app(db):
        data["tiktok_app"] = {"client_key": app["client_key"]}
        secrets["tiktok_client_secret"] = app["client_secret"]
    if (acc := ttp.get_account(db)) and (rt := _safe_decrypt(acc.get("refresh_enc"))) is not None:
        data["tiktok"] = {k: acc.get(k) for k in ("open_id", "display_name", "avatar", "scope", "mode", "privacy_level")}
        secrets["tiktok_refresh_token"] = rt
    out = {"format": FORMAT, "version": __version__, "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
           "data": data, "secrets": None}  # fmt: skip
    if password:
        salt = os.urandom(16)
        out["secrets"] = {"kdf": "pbkdf2-sha256", "iterations": ITERATIONS, "salt": base64.b64encode(salt).decode(),
                          "token": _fernet(password, salt).encrypt(json.dumps(secrets).encode()).decode()}  # fmt: skip
    return out


def _open_secrets(blob: dict | None, password: str | None) -> dict:
    if not blob:
        return {}
    if not password:
        raise PortabilityError("this file contains encrypted keys: enter the password it was exported with")
    try:
        f = _fernet(password, base64.b64decode(blob["salt"]))
        return json.loads(f.decrypt(blob["token"].encode()))
    except (InvalidToken, KeyError, ValueError):
        raise PortabilityError("wrong password (or the file is damaged)") from None


def import_settings(db: Session, payload: dict, *, password: str | None) -> dict:
    from mediafactory.schedule.runner import plan_next
    from mediafactory.sources.adapters import get_adapter
    from mediafactory.youtube import oauth

    if not isinstance(payload, dict) or payload.get("format") != FORMAT:
        raise PortabilityError("this is not a Media Factory settings file")
    data, sec = payload.get("data") or {}, _open_secrets(payload.get("secrets"), password)
    counts = {"providers": 0, "routes": 0, "sources": 0, "schedules": 0, "channels": 0, "skipped": 0}

    for p in data.get("providers", []):
        row = db.scalar(select(AIProvider).where(AIProvider.name == p["name"])) or AIProvider(name=p["name"])
        for k in ("kind", "base_url", "locality", "timeout_s", "max_concurrency", "enabled"):
            if k in p:
                setattr(row, k, p[k])
        if p["name"] in sec.get("providers", {}):
            row.api_key_enc = encrypt(sec["providers"][p["name"]])
        db.add(row)
        counts["providers"] += 1
    db.flush()
    ids = {p.name: p.id for p in db.scalars(select(AIProvider))}

    for r in data.get("routes", []):
        steps = [{"provider_id": ids[s["provider"]], "model": s["model"]} for s in r.get("steps", []) if s.get("provider") in ids]
        row = db.scalar(select(AITaskRoute).where(AITaskRoute.task == r["task"])) or AITaskRoute(task=r["task"])
        row.steps, row.rounds, row.retry_delay_s = steps, r.get("rounds", 3), r.get("retry_delay_s", 3.0)
        db.add(row)
        counts["routes"] += 1

    for s in data.get("sources", []):
        try:
            params = get_adapter(s["adapter"]).validate(dict(s.get("params") or {}))
        except (ValueError, KeyError):
            counts["skipped"] += 1
            continue
        row = db.scalar(select(SourceConnector).where(SourceConnector.name == s["name"])) or SourceConnector(name=s["name"])
        row.adapter, row.params, row.deleted_at = s["adapter"], params, None
        for k in ("enabled", "poll_interval_min", "default_rights", "default_language"):
            if k in s:
                setattr(row, k, s[k])
        db.add(row)
        counts["sources"] += 1

    now = datetime.now(UTC)
    for s in data.get("schedules", []):
        row = db.scalar(select(Schedule).where(Schedule.name == s["name"])) or Schedule(name=s["name"])
        for k in ("kind", "enabled", "times", "weekdays", "timezone", "params"):
            if k in s:
                setattr(row, k, s[k])
        try:
            plan_next(row, now)
        except ValueError:
            counts["skipped"] += 1
            continue
        db.add(row)
        counts["schedules"] += 1

    yt = data.get("youtube") or {}
    if yt.get("client_id") and sec.get("youtube_client_secret"):
        oauth.set_client(db, yt["client_id"], sec["youtube_client_secret"])
    for c in yt.get("channels", []):
        token = sec.get("channels", {}).get(c["channel_id"])
        row = db.scalar(select(YouTubeChannel).where(YouTubeChannel.channel_id == c["channel_id"]))
        if row is None and token is None:
            continue  # a channel cannot be used without its token
        row = row or YouTubeChannel(channel_id=c["channel_id"])
        row.title, row.thumbnail, row.is_default = c.get("title", ""), c.get("thumbnail"), bool(c.get("is_default"))
        if token:
            row.refresh_token_enc = encrypt(token)
        db.add(row)
        counts["channels"] += 1
    if sec.get("reddit"):
        set_reddit_credentials(db, sec["reddit"]["client_id"], sec["reddit"]["client_secret"])
    db.flush()
    for c in data.get("concepts", []):
        row = db.scalar(select(Concept).where(Concept.name == c["name"])) or Concept(name=c["name"])
        chan = db.scalar(select(YouTubeChannel).where(YouTubeChannel.channel_id == c["youtube_channel"])) if c.get("youtube_channel") else None
        for key in ("enabled", "language", "topic", "seconds", "style", "voice", "music", "background", "platforms",
                    "privacy", "ready_buffer", "auto_approve"):
            if key in c:
                setattr(row, key, c[key])
        row.youtube_channel_id = chan.id if chan else None
        db.add(row)
        counts["concepts"] = counts.get("concepts", 0) + 1
    if sec.get("coverr_key"):
        from mediafactory.pipeline.stock import set_coverr_key

        set_coverr_key(db, sec["coverr_key"])
    ig = data.get("instagram") or {}
    if ig.get("user_id") and sec.get("instagram_token"):
        from mediafactory.instagram.publish import save_account

        expires = datetime.fromisoformat(ig["expires_at"]) if ig.get("expires_at") else None
        save_account(db, sec["instagram_token"], info={k: ig.get(k) for k in ("user_id", "username", "account_type")},
                     expires_at=expires)  # fmt: skip
        counts["instagram"] = 1
    from mediafactory.tiktok import publish as ttp

    if (data.get("tiktok_app") or {}).get("client_key") and sec.get("tiktok_client_secret"):
        ttp.set_app(db, data["tiktok_app"]["client_key"], sec["tiktok_client_secret"])
    tk = data.get("tiktok") or {}
    if tk.get("open_id") and sec.get("tiktok_refresh_token"):
        # the access token is not carried: it is refreshed on first use (expiry set in the past)
        ttp.save_tokens(db, {"access_token": "-", "refresh_token": sec["tiktok_refresh_token"], "expires_in": -1,
                             "scope": tk.get("scope")}, info=tk)  # fmt: skip
        acc = ttp.get_account(db)
        if tk.get("mode") == "direct" and tk.get("privacy_level"):
            ttp._store(db, {**acc, "mode": "direct", "privacy_level": tk["privacy_level"]})
        counts["tiktok"] = 1
    db.flush()
    return counts
