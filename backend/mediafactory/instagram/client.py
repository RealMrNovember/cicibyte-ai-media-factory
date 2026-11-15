"""Instagram Graph API (Instagram API with Instagram Login): account check, token refresh and Reels upload.

Only professional accounts (Creator or Business) can publish through the API; personal accounts get a
manual "download + copy caption" flow in the app instead. The video is sent directly with a resumable
upload, so the server does not need a public address.
"""

import re
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

GRAPH = "https://graph.instagram.com/v23.0"
REFRESH_URL = "https://graph.instagram.com/refresh_access_token"
CAPTION_MAX = 2200
HASHTAG_MAX = 30
PROCESS_TIMEOUT_S = 15 * 60
REFRESH_EVERY = timedelta(days=7)
REFRESH_BEFORE = timedelta(days=10)


class InstagramError(Exception):
    def __init__(self, message: str, *, transient: bool = False):
        super().__init__(message)
        self.transient = transient


def _http(http: httpx.Client | None) -> httpx.Client:
    return http or httpx.Client(timeout=httpx.Timeout(60, write=900, read=300))


def _check(r: httpx.Response) -> dict:
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code >= 400 or (isinstance(data, dict) and "error" in data):
        err = (data.get("error") or {}) if isinstance(data, dict) else {}
        message = err.get("error_user_msg") or err.get("message") or r.text[:200] or f"HTTP {r.status_code}"
        transient = r.status_code >= 500 or r.status_code == 429 or bool(err.get("is_transient"))
        raise InstagramError(f"Instagram: {message}", transient=transient)
    return data


def build_caption(script: dict, *, credit: str | None = None) -> str:
    tags = []
    for t in script.get("tags") or []:
        word = re.sub(r"[\W_]+", "", str(t))
        if word and word.lower() not in {x.lower() for x in tags}:
            tags.append(word)
    hashtags = " ".join("#" + t for t in tags[:HASHTAG_MAX])
    head = "\n\n".join(x for x in ((script.get("title") or "").strip(), (script.get("description") or "").strip()) if x)
    tail = "\n\n".join(x for x in (credit or "", hashtags) if x)
    room = CAPTION_MAX - len(tail) - 2
    return (head[:room].rstrip() + ("\n\n" + tail if tail else "")).strip()


def account_info(token: str, *, http: httpx.Client | None = None) -> dict:
    c = _http(http)
    data = _check(c.get(f"{GRAPH}/me", params={"fields": "user_id,username,account_type", "access_token": token}))
    kind = str(data.get("account_type") or "").upper()
    if kind not in ("BUSINESS", "MEDIA_CREATOR", "CREATOR"):
        raise InstagramError("this is a personal Instagram account: only professional (Creator or Business) accounts "
                             "can publish through the API. Switch for free in Instagram → Settings → Account type, "
                             "or use “Share manually”.")  # fmt: skip
    return {"user_id": str(data["user_id"]), "username": data.get("username", ""), "account_type": kind}


def refresh_token(token: str, *, http: httpx.Client | None = None) -> tuple[str, datetime]:
    c = _http(http)
    data = _check(c.get(REFRESH_URL, params={"grant_type": "ig_refresh_token", "access_token": token}))
    return data["access_token"], datetime.now(UTC) + timedelta(seconds=int(data.get("expires_in", 5184000)))


def refresh_due(account: dict, *, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    refreshed = datetime.fromisoformat(account.get("refreshed_at") or "1970-01-01T00:00:00+00:00")
    expires = datetime.fromisoformat(account.get("expires_at") or "1970-01-01T00:00:00+00:00")
    return now - refreshed > REFRESH_EVERY or expires - now < REFRESH_BEFORE


def publish_reel(
    token: str, user_id: str, video: Path, caption: str, *, http: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep, log: Callable[[str], None] = lambda m: None,
) -> tuple[str, str]:  # fmt: skip
    """Create a Reels container, upload the file, wait for processing, publish. Returns (media id, permalink)."""
    c = _http(http)
    box = _check(c.post(f"{GRAPH}/{user_id}/media", data={
        "media_type": "REELS", "upload_type": "resumable", "caption": caption, "share_to_feed": "true",
        "access_token": token,
    }))  # fmt: skip
    container, uri = box["id"], box.get("uri") or f"https://rupload.facebook.com/ig-api-upload/v23.0/{box['id']}"
    size = video.stat().st_size
    log(f"uploading {size / 1e6:.1f} MB to Instagram")
    with video.open("rb") as fh:
        _check(c.post(uri, content=fh.read(), headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)}))
    waited, delay = 0.0, 5.0
    while True:
        st = _check(c.get(f"{GRAPH}/{container}", params={"fields": "status_code,status", "access_token": token}))
        code = st.get("status_code")
        if code in ("FINISHED", "PUBLISHED"):
            break
        if code in ("ERROR", "EXPIRED"):
            raise InstagramError(f"Instagram could not process the video: {st.get('status') or code}")
        if waited >= PROCESS_TIMEOUT_S:
            raise InstagramError("Instagram is still processing the video after 15 minutes", transient=True)
        sleep(delay)
        waited += delay
        delay = min(delay * 1.5, 30.0)
    log("processed by Instagram, publishing")
    media_id = _check(c.post(f"{GRAPH}/{user_id}/media_publish", data={"creation_id": container, "access_token": token}))["id"]
    try:
        link = _check(c.get(f"{GRAPH}/{media_id}", params={"fields": "permalink", "access_token": token})).get("permalink")
    except InstagramError:
        link = None
    return str(media_id), link or "https://www.instagram.com/"
