from mediafactory.sources.adapters.base import FetchContext, RawItem, http_url, int_in, register, translate_errors
from mediafactory.sources.feeds import parse_feed
from mediafactory.sources.text import normalize_text, strip_html


@register
class RssAdapter:
    key = "rss"

    def validate(self, params: dict) -> dict:
        return {"url": http_url(params.get("url")), "max_items": int_in(params, "max_items", 25, 1, 100)}

    def fetch(self, params: dict, ctx: FetchContext) -> list[RawItem]:
        with translate_errors():
            entries = parse_feed(ctx.fetcher.get(params["url"]).content)
        items = []
        for e in entries[: params["max_items"]]:
            items.append(
                RawItem(
                    external_id=e.id,
                    url=e.link,
                    title=strip_html(e.title),
                    text=normalize_text(e.content_html or e.summary_html),
                    author=e.author,
                    published_at=e.published_at,
                )
            )
        return items
