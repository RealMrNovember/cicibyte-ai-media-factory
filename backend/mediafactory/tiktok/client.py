"""TikTok Content Posting API: sign-in (Login Kit for Desktop, PKCE), token refresh and video upload.

Two ways to post:
- draft (scope video.upload): the video lands in the creator's TikTok inbox and they post it from the app.
  Works for any app, no TikTok review needed.
- direct (scope video.publish): posted straight to the profile. Until TikTok has audited the app, such
  posts are only visible to the creator (SELF_ONLY).
The file is sent with FILE_UPLOAD in chunks, so the server needs no public address.
"""

import hashlib
import secrets
import time
import urllib.parse
from collections.abc import Callable
from pathlib import Path

import httpx

AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
API = "https://open.tiktokapis.com/v2"
TOKEN_URL = f"{API}/oauth/token/"  # noqa: S105 (endpoint, not a secret)
DRAFT_SCOPES = ["user.info.basic", "video.upload"]
DIRECT_SCOPE = "video.publish"
CHUNK = 10 * 2**20
PROCESS_TIMEOUT_S = 15 * 60

# TikTok error codes worth a clearer sentence than the API's message.
HINTS = {
    "spam_risk_too_many_pending_share": "TikTok allows only 5 drafts waiting in the inbox per day: post or delete "
                                        "the waiting ones in the TikTok app, then try again",
    "spam_risk_user_banned_from_posting": "TikTok does not let this account post right now",
    "scope_not_authorized": "TikTok did not grant this permission: reconnect TikTok in Settings",
    "access_token_invalid": "TikTok access ended: reconnect TikTok in Settings",
    "unaudited_client_can_only_post_to_private_accounts": "until TikTok approves your app (audit), direct posts "
                                                          "need a private TikTok account: use draft mode instead",
}  # fmt: skip


class TikTokError(Exception):
    def __init__(self, message: str, *, transient: bool = False, reauth: bool = False):
        super().__init__(message)
        self.transient = transient
        self.reauth = reauth  # the connection must be made again


def _http(http: httpx.Client | None) -> httpx.Client:
    return http or httpx.Client(timeout=httpx.Timeout(60, write=900, read=300))


def _check(r: httpx.Response) -> dict:
    try:
        body = r.json()
    except ValueError:
        body = {}
    err = (body.get("error") or {}) if isinstance(body, dict) else {}
    code = err.get("code", "ok") if isinstance(err, dict) else "error"
    if r.status_code >= 400 or code != "ok":
        message = HINTS.get(code) or (err.get("message") if isinstance(err, dict) else None) or r.text[:200] or f"HTTP {r.status_code}"
        transient = r.status_code >= 500 or r.status_code == 429 or code == "rate_limit_exceeded"
        raise TikTokError(f"TikTok: {message}", transient=transient, reauth=code in ("access_token_invalid", "scope_not_authorized"))
    return body.get("data") or {}


def pkce() -> tuple[str, str]:
    """(verifier, challenge). TikTok's desktop flow wants the challenge as the HEX sha256, not base64url."""
    verifier = secrets.token_urlsafe(64)[:96]
    return verifier, hashlib.sha256(verifier.encode()).hexdigest()


def auth_url(client_key: str, redirect_uri: str, state: str, challenge: str, *, direct: bool = False) -> str:
    scopes = DRAFT_SCOPES + ([DIRECT_SCOPE] if direct else [])
    q = {"client_key": client_key, "response_type": "code", "scope": ",".join(scopes), "redirect_uri": redirect_uri,
         "state": state, "code_challenge": challenge, "code_challenge_method": "S256"}  # fmt: skip
    return AUTH_URL + "?" + urllib.parse.urlencode(q)


def _token(data: dict, http: httpx.Client | None) -> dict:
    r = _http(http).post(TOKEN_URL, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        body = r.json()
    except ValueError:
        body = {}
    if r.status_code != 200 or body.get("error") or not body.get("access_token"):
        detail = body.get("error_description") or body.get("error") or r.text[:200]
        raise TikTokError(f"TikTok refused the sign-in: {detail}", transient=r.status_code >= 500,
                          reauth=body.get("error") in ("invalid_grant", "invalid_request"))  # fmt: skip
    return body


def exchange_code(app: dict, code: str, verifier: str, redirect_uri: str, *, http: httpx.Client | None = None) -> dict:
    return _token({"client_key": app["client_key"], "client_secret": app["client_secret"], "code": code,
                   "grant_type": "authorization_code", "redirect_uri": redirect_uri, "code_verifier": verifier}, http)  # fmt: skip


def refresh(app: dict, refresh_token: str, *, http: httpx.Client | None = None) -> dict:
    """New tokens. TikTok returns a NEW refresh token each time: the old one stops working, store this one."""
    return _token({"client_key": app["client_key"], "client_secret": app["client_secret"],
                   "grant_type": "refresh_token", "refresh_token": refresh_token}, http)  # fmt: skip


def user_info(token: str, *, http: httpx.Client | None = None) -> dict:
    data = _check(_http(http).get(f"{API}/user/info/", params={"fields": "open_id,display_name,avatar_url"},
                                  headers={"Authorization": f"Bearer {token}"}))  # fmt: skip
    user = data.get("user") or {}
    return {"open_id": user.get("open_id"), "display_name": user.get("display_name") or "TikTok", "avatar": user.get("avatar_url")}


def creator_info(token: str, *, http: httpx.Client | None = None) -> dict:
    """Nickname, the privacy levels this creator may choose, disabled interactions, longest allowed video."""
    return _check(_http(http).post(f"{API}/post/publish/creator_info/query/", json={},
                                   headers={"Authorization": f"Bearer {token}"}))  # fmt: skip


def chunk_plan(size: int) -> tuple[int, int]:
    """(chunk_size, total_chunk_count): whole file under 20 MB, else 10 MB chunks; the last one takes the rest (< 20 MB)."""
    if size < 2 * CHUNK:
        return size, 1
    return CHUNK, size // CHUNK


def send_video(
    token: str, video: Path, *, post_info: dict | None = None, http: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep, log: Callable[[str], None] = lambda m: None,
) -> dict:  # fmt: skip
    """Upload the file: to the inbox as a draft (post_info None) or posted directly. Waits until TikTok has it.

    Returns {"publish_id", "status", "post_id"} (post_id only for a public direct post).
    """
    c = _http(http)
    auth = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"}
    size = video.stat().st_size
    chunk, count = chunk_plan(size)
    body: dict = {"source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": chunk, "total_chunk_count": count}}
    if post_info is not None:
        body = {"post_info": post_info, **body}
    url = f"{API}/post/publish/video/init/" if post_info is not None else f"{API}/post/publish/inbox/video/init/"
    data = _check(c.post(url, json=body, headers=auth))
    publish_id, upload_url = data["publish_id"], data["upload_url"]
    log(f"uploading {size / 1e6:.1f} MB to TikTok in {count} part(s)")
    with video.open("rb") as fh:
        for i in range(count):
            start = i * chunk
            part = fh.read(chunk if i < count - 1 else size - start)
            end = start + len(part) - 1
            r = c.put(upload_url, content=part, headers={"Content-Type": "video/mp4", "Content-Length": str(len(part)),
                                                         "Content-Range": f"bytes {start}-{end}/{size}"})  # fmt: skip
            if r.status_code not in (200, 201, 206):
                raise TikTokError(f"TikTok refused part {i + 1} of the upload (HTTP {r.status_code})", transient=r.status_code >= 500)
    done = "PUBLISH_COMPLETE" if post_info is not None else "SEND_TO_USER_INBOX"
    waited, delay = 0.0, 5.0
    while True:
        st = _check(c.post(f"{API}/post/publish/status/fetch/", json={"publish_id": publish_id}, headers=auth))
        status = st.get("status")
        if status in (done, "PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"):
            ids = st.get("publicaly_available_post_id") or st.get("publicly_available_post_id") or []
            return {"publish_id": publish_id, "status": status, "post_id": str(ids[0]) if ids else None}
        if status == "FAILED":
            raise TikTokError(f"TikTok could not take the video: {st.get('fail_reason') or 'unknown reason'}")
        if waited >= PROCESS_TIMEOUT_S:
            raise TikTokError("TikTok is still processing the video after 15 minutes", transient=True)
        sleep(delay)
        waited += delay
        delay = min(delay * 1.5, 30.0)
