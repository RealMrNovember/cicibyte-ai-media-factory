"""Background clips from free stock libraries: Coverr (search with your own API key) and Mixkit (paste a link).

Both licences allow free use in YouTube and Instagram videos; the licence and the source link are stored next
to every clip. Downloads only go to the libraries' own hosts and are size-capped.
"""

import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from mediafactory.core.crypto import decrypt, encrypt
from mediafactory.db.models import SystemSetting
from mediafactory.pipeline.backgrounds import SAFE_NAME, add_clip

COVERR = "https://api.coverr.co"
KEY = "coverr"
MAX_BYTES = 400 * 1024 * 1024
ALLOWED_HOSTS = ("coverr.co", "mixkit.co")  # and their sub-domains (cdn., storage., assets., …)
COVERR_LICENCE = ("Coverr License — free for commercial and personal use; credit Coverr and the creator; "
                  "do not register in YouTube Content ID")  # fmt: skip
MIXKIT_LICENCE = "Mixkit Stock Video Free License — free for commercial and personal use, no attribution required"


class StockError(Exception):
    pass


def coverr_key(db: Session) -> str | None:
    row = db.get(SystemSetting, KEY)
    try:
        return decrypt(row.value["key_enc"]) if row and isinstance(row.value, dict) and row.value.get("key_enc") else None
    except Exception:  # noqa: BLE001 - a key from another secret is unusable
        return None


def set_coverr_key(db: Session, key: str | None) -> None:
    row = db.get(SystemSetting, KEY)
    if not key:
        if row is not None:
            db.delete(row)
        return
    value = {"key_enc": encrypt(key.strip())}
    if row is None:
        db.add(SystemSetting(key=KEY, value=value))
    else:
        row.value = value


def _client(http: httpx.Client | None = None) -> httpx.Client:
    return http or httpx.Client(timeout=httpx.Timeout(30, read=300), follow_redirects=False)


def _check(r: httpx.Response) -> dict:
    if r.status_code in (401, 403):
        raise StockError("Coverr refused the API key — check it in Settings → Stock clips")
    if r.status_code == 429:
        raise StockError("Coverr's request limit is reached for now — try again later")
    if r.status_code >= 400:
        raise StockError(f"Coverr error {r.status_code}: {r.text[:200]}")
    return r.json()


def _item(hit: dict) -> dict:
    urls = hit.get("urls") or {}
    return {"id": str(hit["id"]), "title": hit.get("title") or "", "thumbnail": hit.get("thumbnail"),
            "preview": urls.get("mp4_preview") or urls.get("mp4"), "duration": hit.get("duration"),
            "vertical": bool(hit.get("is_vertical"))}  # fmt: skip


def coverr_search(key: str, query: str, *, page: int = 0, http: httpx.Client | None = None) -> dict:
    r = _client(http).get(f"{COVERR}/videos", headers={"x-api-key": key},
                          params={"query": query, "page": page, "page_size": 24, "urls": "true"})  # fmt: skip
    data = _check(r)
    return {"items": [_item(h) for h in data.get("hits") or []], "page": data.get("page", page), "pages": data.get("pages", 1)}


def _host_ok(url: str) -> bool:
    p = urlparse(url)
    host = (p.hostname or "").lower()
    return p.scheme == "https" and any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)


def _download(url: str, dest: Path, *, http: httpx.Client | None = None) -> Path:
    if not _host_ok(url):
        raise StockError(f"downloads are only allowed from Coverr and Mixkit, not from host {urlparse(url).hostname}")
    size = 0
    try:
        with _client(http).stream("GET", url) as r:
            if r.status_code != 200:
                raise StockError(f"download failed (HTTP {r.status_code})")
            with dest.open("wb") as f:
                for chunk in r.iter_bytes(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise StockError(f"the clip is too large (over {MAX_BYTES // (1024 * 1024)} MB)")
                    f.write(chunk)
    except BaseException:
        dest.unlink(missing_ok=True)
        raise
    return dest


def _slug(text: str) -> str:
    return (SAFE_NAME.sub("-", text.lower()).strip("-.") or "clip")[:60]


def _store(data_dir: Path, tmp: Path, name: str, *, licence: str, source: str, tags) -> Path:
    with tmp.open("rb") as f:
        return add_clip(data_dir, name, f, licence=licence, source=source, tags=tags)


def coverr_import(data_dir: Path, key: str, video_id: str, *, tags=None, http: httpx.Client | None = None) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,64}", video_id or ""):
        raise StockError("unknown Coverr video")
    c = _client(http)
    hit = _check(c.get(f"{COVERR}/videos/{video_id}", headers={"x-api-key": key}, params={"urls": "true"}))
    urls = hit.get("urls") or {}
    url = urls.get("mp4_download") or urls.get("mp4")
    if not url:
        raise StockError("Coverr returned no download link for this video")
    with tempfile.TemporaryDirectory() as td:
        tmp = _download(url, Path(td) / "clip.mp4", http=c)
        clip = _store(data_dir, tmp, f"coverr-{_slug(hit.get('title') or video_id)}.mp4", licence=COVERR_LICENCE,
                      source=f"https://coverr.co/videos/{video_id}", tags=tags)  # fmt: skip
    try:  # Coverr asks API apps to report downloads; never fail the import over it
        c.patch(f"{COVERR}/videos/{video_id}/stats/downloads", headers={"x-api-key": key})
    except httpx.HTTPError:
        pass
    return clip


def mixkit_id(url: str) -> str | None:
    if not _host_ok(url or "") or "mixkit.co" not in (urlparse(url).hostname or ""):
        return None
    m = re.search(r"/videos/(\d+)/|-(\d+)/?$", urlparse(url).path)
    return (m.group(1) or m.group(2)) if m else None


def mixkit_import(data_dir: Path, url: str, *, tags=None, http: httpx.Client | None = None) -> Path:
    vid = mixkit_id(url)
    if vid is None:
        raise StockError("paste a Mixkit video link, e.g. https://mixkit.co/free-stock-video/…-12345/")
    c = _client(http)
    slug = re.sub(rf"-?{vid}/?$", "", urlparse(url).path.rstrip("/").split("/")[-1]) if "free-stock-video" in url else ""
    for size in ("1080", "720", "360"):  # Mixkit serves each clip in these sizes
        candidate = f"https://assets.mixkit.co/videos/{vid}/{vid}-{size}.mp4"
        if c.head(candidate).status_code == 200:
            break
    else:
        raise StockError("Mixkit has no downloadable file for this video")
    with tempfile.TemporaryDirectory() as td:
        tmp = _download(candidate, Path(td) / "clip.mp4", http=c)
        return _store(data_dir, tmp, f"mixkit-{_slug(slug or vid)}.mp4", licence=MIXKIT_LICENCE, source=url, tags=tags)
