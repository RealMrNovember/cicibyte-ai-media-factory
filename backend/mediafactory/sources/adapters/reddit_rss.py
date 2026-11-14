"""Reddit through its public Atom feeds (no credentials). Reddit content belongs to its authors: items start
with rights_status 'unknown' and are only used in 'inspired' mode unless rights are granted."""

import re

from mediafactory.sources.adapters.base import (
    FetchContext,
    RawItem,
    boolean,
    choice,
    int_in,
    register,
    require_entries,
    resolve_link,
    translate_errors,
)  # fmt: skip
from mediafactory.sources.feeds import parse_feed
from mediafactory.sources.text import normalize_text, strip_html

SUBREDDIT = re.compile(r"^[A-Za-z0-9_]{2,21}$")
SORTS = ("hot", "new", "top", "rising")
TIMES = ("hour", "day", "week", "month", "year", "all")
NSFW = re.compile(r"\bnsfw\b", re.IGNORECASE)


def subreddit(params: dict) -> str:
    value = str(params.get("subreddit", "")).strip()
    if value.lower().startswith("r/"):
        value = value[2:]
    if not SUBREDDIT.match(value):
        raise ValueError("'subreddit' must be a subreddit name (2-21 letters, digits or _)")
    return value


def clean_author(author: str | None) -> str | None:
    if not author:
        return None
    return author.removeprefix("/u/").removeprefix("u/") or None


@register
class RedditRssAdapter:
    key = "reddit_rss"

    def validate(self, params: dict) -> dict:
        return {
            "subreddit": subreddit(params),
            "sort": choice(params, "sort", "top", SORTS),
            "time": choice(params, "time", "day", TIMES),
            "min_chars": int_in(params, "min_chars", 400, 0, 50_000),
            "max_items": int_in(params, "max_items", 25, 1, 100),
            "include_nsfw": boolean(params, "include_nsfw", False),
        }

    def fetch(self, params: dict, ctx: FetchContext) -> list[RawItem]:
        url = f"https://www.reddit.com/r/{params['subreddit']}/{params['sort']}/.rss?t={params['time']}"
        with translate_errors():
            entries = require_entries(parse_feed(ctx.fetcher.get(url).content))
        items = []
        for e in entries[: params["max_items"]]:
            title = strip_html(e.title)
            text = normalize_text(e.content_html or e.summary_html)
            if len(text) < params["min_chars"]:
                continue
            if not params["include_nsfw"] and NSFW.search(title):
                continue
            items.append(
                RawItem(
                    external_id=e.id,
                    url=resolve_link(url, e.link),
                    title=title,
                    text=text,
                    author=clean_author(e.author),
                    published_at=e.published_at,
                    meta={"subreddit": params["subreddit"]},
                )
            )
        return items
