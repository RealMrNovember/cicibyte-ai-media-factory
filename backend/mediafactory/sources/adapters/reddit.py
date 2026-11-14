"""Official Reddit API (application-only OAuth, client_credentials). Credentials are set by an admin in
Settings → Source credentials; without them this adapter reports 'not configured'."""

import base64
import json
import threading
import time
from datetime import UTC, datetime

from mediafactory.core.net import FetchError
from mediafactory.sources.adapters.base import (
    AdapterError,
    FetchContext,
    RawItem,
    boolean,
    choice,
    int_in,
    register,
)  # fmt: skip
from mediafactory.sources.adapters.reddit_rss import SORTS, TIMES, subreddit
from mediafactory.sources.text import normalize_text, strip_html

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API = "https://oauth.reddit.com"
NOT_CONFIGURED = "Reddit API credentials are not configured (Settings → Source credentials)"

_clock = time.monotonic
_tokens: dict[str, tuple[str, float]] = {}
_lock = threading.Lock()


def reset_token_cache() -> None:
    with _lock:
        _tokens.clear()


def _token(ctx: FetchContext, creds: dict) -> str:
    client_id = creds["client_id"]
    with _lock:
        cached = _tokens.get(client_id)
        if cached and cached[1] > _clock():
            return cached[0]
    basic = base64.b64encode(f"{client_id}:{creds['client_secret']}".encode()).decode()
    try:
        r = ctx.fetcher.post(
            TOKEN_URL, data={"grant_type": "client_credentials"}, headers={"Authorization": f"Basic {basic}"}
        )
    except FetchError as exc:
        if exc.status in (400, 401, 403):
            raise AdapterError(f"Reddit rejected the API credentials (HTTP {exc.status})", retryable=False) from None
        raise AdapterError(str(exc), retryable=exc.retryable) from None
    try:
        data = json.loads(r.text)
        token, expires_in = data["access_token"], int(data.get("expires_in", 3600))
    except (ValueError, KeyError, TypeError):
        raise AdapterError("unexpected token response from Reddit", retryable=True) from None
    with _lock:
        _tokens[client_id] = (token, _clock() + max(60, expires_in - 60))
    return token


@register
class RedditApiAdapter:
    key = "reddit"

    def validate(self, params: dict) -> dict:
        return {
            "subreddit": subreddit(params),
            "sort": choice(params, "sort", "top", SORTS),
            "time": choice(params, "time", "day", TIMES),
            "min_score": int_in(params, "min_score", 0, 0, 10_000_000),
            "min_chars": int_in(params, "min_chars", 400, 0, 50_000),
            "max_items": int_in(params, "max_items", 25, 1, 100),
            "include_nsfw": boolean(params, "include_nsfw", False),
        }

    def fetch(self, params: dict, ctx: FetchContext) -> list[RawItem]:
        creds = ctx.credentials
        if not creds or not creds.get("client_id") or not creds.get("client_secret"):
            raise AdapterError(NOT_CONFIGURED, retryable=False)
        token = _token(ctx, creds)
        url = (
            f"{API}/r/{params['subreddit']}/{params['sort']}"
            f"?t={params['time']}&limit={params['max_items']}&raw_json=1"
        )
        try:
            r = ctx.fetcher.get(url, headers={"Authorization": f"Bearer {token}"})
        except FetchError as exc:
            if exc.status in (401, 403):
                with _lock:
                    _tokens.pop(creds["client_id"], None)  # token revoked or app changed: get a new one next time
                raise AdapterError(f"Reddit refused the request (HTTP {exc.status})", retryable=False) from None
            raise AdapterError(str(exc), retryable=exc.retryable) from None
        return self._parse(r.text, params)

    def _parse(self, body: str, params: dict) -> list[RawItem]:
        try:
            children = json.loads(body)["data"]["children"]
        except (ValueError, KeyError, TypeError):
            raise AdapterError("unexpected listing response from Reddit", retryable=True) from None
        items = []
        for child in children:
            d = child.get("data") if isinstance(child, dict) else None
            if not isinstance(d, dict) or d.get("stickied"):
                continue
            if d.get("over_18") and not params["include_nsfw"]:
                continue
            if int(d.get("score") or 0) < params["min_score"]:
                continue
            text = normalize_text(d.get("selftext") or "")
            if len(text) < params["min_chars"]:
                continue
            created = d.get("created_utc")
            items.append(
                RawItem(
                    external_id=f"t3_{d.get('id')}",
                    url=f"https://www.reddit.com{d.get('permalink', '')}",
                    title=strip_html(d.get("title") or ""),
                    text=text,
                    author=d.get("author") or None,
                    published_at=datetime.fromtimestamp(created, UTC) if isinstance(created, int | float) else None,
                    meta={"subreddit": params["subreddit"], "score": d.get("score"), "over_18": bool(d.get("over_18"))},
                )
            )
        return items
