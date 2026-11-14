"""Resumable upload of a finished Short, with YouTube-side scheduling (private + publishAt)."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx

from mediafactory.youtube.oauth import YouTubeError

UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
THUMBNAIL_URL = "https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
CATEGORY_ENTERTAINMENT = "24"


def build_metadata(script: dict, *, language: str, privacy: str, publish_at: datetime | None) -> dict:
    title = re.sub(r"[<>]", "", script.get("title") or "Short").strip()[:95]
    tags = [re.sub(r"[<>,]", "", t).strip() for t in script.get("tags") or [] if t and t.strip()][:15]
    hashtags = " ".join("#" + re.sub(r"\W+", "", t) for t in tags[:3] if re.sub(r"\W+", "", t))
    description = ((script.get("description") or "").strip() + f"\n\n#shorts {hashtags}").strip()[:4800]
    status: dict = {"privacyStatus": privacy, "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True}
    if publish_at is not None:  # YouTube publishes it at that moment; it must be private until then
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return {
        "snippet": {"title": title, "description": description, "tags": tags, "categoryId": CATEGORY_ENTERTAINMENT,
                    "defaultLanguage": language, "defaultAudioLanguage": language},
        "status": status,
    }  # fmt: skip


def upload_video(token: str, video: Path, metadata: dict, *, http: httpx.Client | None = None) -> str:
    """Returns the YouTube video id."""
    client = http or httpx.Client(timeout=httpx.Timeout(60, write=600, read=600))
    size = video.stat().st_size
    r = client.post(
        UPLOAD_URL, params={"uploadType": "resumable", "part": "snippet,status"},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)},
        content=json.dumps(metadata).encode(),
    )  # fmt: skip
    if r.status_code != 200 or "location" not in r.headers:
        raise YouTubeError(f"YouTube refused the upload: {r.text[:400]}")
    with video.open("rb") as f:
        r = client.put(r.headers["location"], content=f.read(),
                       headers={"Authorization": f"Bearer {token}", "Content-Type": "video/mp4"})  # fmt: skip
    if r.status_code not in (200, 201):
        raise YouTubeError(f"YouTube upload failed: {r.text[:400]}")
    return r.json()["id"]


def set_thumbnail(token: str, video_id: str, image: Path, *, http: httpx.Client | None = None) -> str | None:
    """Upload the cover image. Returns an error text instead of raising (custom thumbnails need a verified
    channel; a refused cover must not fail the upload)."""
    client = http or httpx.Client(timeout=120)
    r = client.post(THUMBNAIL_URL, params={"videoId": video_id}, content=image.read_bytes(),
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "image/jpeg"})  # fmt: skip
    return None if r.status_code == 200 else f"HTTP {r.status_code}: {r.text[:200]}"
