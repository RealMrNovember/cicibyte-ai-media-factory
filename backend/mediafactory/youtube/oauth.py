"""OAuth 2.0 for YouTube with the user's own Google client (type "Desktop app"), PKCE, loopback redirect."""

import base64
import hashlib
import secrets
import time
import urllib.parse

import httpx
from sqlalchemy.orm import Session

from mediafactory.core.crypto import decrypt, encrypt
from mediafactory.db.models import SystemSetting

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 (endpoint, not a secret)
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
# force-ssl adds captions and playlists; channels connected before it keep uploading and are asked to reconnect for those.
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly",
          "https://www.googleapis.com/auth/youtube.force-ssl"]  # fmt: skip
CLIENT_KEY = "youtube_client"
PENDING_PREFIX = "youtube_pending:"
PENDING_TTL_S = 15 * 60


class YouTubeError(Exception):
    def __init__(self, message: str, *, revoked: bool = False):
        super().__init__(message)
        self.revoked = revoked  # the channel's access was withdrawn: it must be reconnected


def get_client(db: Session) -> dict | None:
    row = db.get(SystemSetting, CLIENT_KEY)
    if not row or not isinstance(row.value, dict) or not row.value.get("client_id"):
        return None
    return {"client_id": row.value["client_id"], "client_secret": decrypt(row.value["client_secret_enc"])}


def set_client(db: Session, client_id: str, client_secret: str) -> None:
    value = {"client_id": client_id.strip(), "client_secret_enc": encrypt(client_secret.strip())}
    row = db.get(SystemSetting, CLIENT_KEY)
    if row is None:
        db.add(SystemSetting(key=CLIENT_KEY, value=value))
    else:
        row.value = value


def start_auth(db: Session, redirect_uri: str) -> str:
    client = get_client(db)
    if client is None:
        raise YouTubeError("add your Google OAuth client id and secret first")
    state, verifier = secrets.token_urlsafe(24), secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    db.add(SystemSetting(key=PENDING_PREFIX + state,
                         value={"verifier": verifier, "redirect_uri": redirect_uri, "expires": time.time() + PENDING_TTL_S}))  # fmt: skip
    q = {
        "client_id": client["client_id"], "redirect_uri": redirect_uri, "response_type": "code",
        "scope": " ".join(SCOPES), "access_type": "offline", "prompt": "consent", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256", "include_granted_scopes": "true",
    }  # fmt: skip
    return AUTH_URL + "?" + urllib.parse.urlencode(q)


def take_pending(db: Session, state: str) -> dict:
    row = db.get(SystemSetting, PENDING_PREFIX + state) if state else None
    if row is None:
        raise YouTubeError("this sign-in link is unknown or was already used — start again from Settings")
    value = dict(row.value)
    db.delete(row)
    if value.get("expires", 0) < time.time():
        raise YouTubeError("this sign-in link expired — start again from Settings")
    return value


def exchange_code(client: dict, code: str, verifier: str, redirect_uri: str, *, http: httpx.Client | None = None) -> dict:
    data = {"code": code, "client_id": client["client_id"], "client_secret": client["client_secret"],
            "redirect_uri": redirect_uri, "grant_type": "authorization_code", "code_verifier": verifier}  # fmt: skip
    r = (http or httpx).post(TOKEN_URL, data=data, timeout=30)
    if r.status_code != 200:
        raise YouTubeError(f"Google refused the sign-in: {r.text[:300]}")
    tokens = r.json()
    if not tokens.get("refresh_token"):
        raise YouTubeError("Google did not return a refresh token; remove the app's access in your Google account and retry")
    return tokens


def access_token(client: dict, refresh_token: str, *, http: httpx.Client | None = None) -> str:
    data = {"client_id": client["client_id"], "client_secret": client["client_secret"],
            "refresh_token": refresh_token, "grant_type": "refresh_token"}  # fmt: skip
    r = (http or httpx).post(TOKEN_URL, data=data, timeout=30)
    if r.status_code != 200:
        revoked = r.status_code in (400, 401) and "invalid_grant" in r.text
        raise YouTubeError(f"could not refresh YouTube access (reconnect the channel): {r.text[:300]}", revoked=revoked)
    return r.json()["access_token"]


def my_channel(token: str, *, http: httpx.Client | None = None) -> dict:
    r = (http or httpx).get(CHANNELS_URL, params={"part": "snippet", "mine": "true"},
                            headers={"Authorization": f"Bearer {token}"}, timeout=30)  # fmt: skip
    if r.status_code != 200 or not r.json().get("items"):
        raise YouTubeError(f"no YouTube channel found for this Google account: {r.text[:300]}")
    item = r.json()["items"][0]
    thumbs = item["snippet"].get("thumbnails", {})
    return {"channel_id": item["id"], "title": item["snippet"].get("title", ""),
            "thumbnail": (thumbs.get("default") or {}).get("url")}  # fmt: skip
