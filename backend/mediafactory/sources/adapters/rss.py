from mediafactory.sources.adapters.base import (
    FetchContext,
    RawItem,
    http_url,
    int_in,
    register,
    require_entries,
    resolve_link,
    translate_errors,
)  # fmt: skip
from mediafactory.sources.feeds import parse_feed
from mediafactory.sources.text import extract_article, normalize_text, strip_html

FULL_TEXT_BELOW = 1200  # feed text shorter than this is replaced by the article page when full_text is on


@register
class RssAdapter:
    key = "rss"

    def validate(self, params: dict) -> dict:
        return {
            "url": http_url(params.get("url")),
            "max_items": int_in(params, "max_items", 25, 1, 100),
            "full_text": bool(params.get("full_text", False)),
            "min_chars": int_in(params, "min_chars", 0, 0, 100_000),
        }

    def _article(self, url: str, ctx: FetchContext) -> str:
        """Readable text of the linked page, or "" (robots.txt refusal or any fetch problem)."""
        try:
            if not ctx.fetcher.robots_allowed(url):
                return ""
            page = ctx.fetcher.get(url, headers={"Accept": "text/html,application/xhtml+xml"})
            return normalize_text(extract_article(page.text)[1])
        except Exception:
            return ""

    def fetch(self, params: dict, ctx: FetchContext) -> list[RawItem]:
        with translate_errors():
            entries = require_entries(parse_feed(ctx.fetcher.get(params["url"]).content))
        items = []
        for e in entries[: params["max_items"]]:
            url = resolve_link(params["url"], e.link)
            text = normalize_text(e.content_html or e.summary_html)
            if params.get("full_text") and url and len(text) < FULL_TEXT_BELOW:
                text = max(text, self._article(url, ctx), key=len)
            if len(text) < params.get("min_chars", 0):
                continue
            items.append(
                RawItem(
                    external_id=e.id,
                    url=url,
                    title=strip_html(e.title),
                    text=text,
                    author=e.author,
                    published_at=e.published_at,
                )
            )
        return items
