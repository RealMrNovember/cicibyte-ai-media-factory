from mediafactory.sources.adapters.base import AdapterError, FetchContext, RawItem, http_url, register, translate_errors
from mediafactory.sources.text import extract_article, normalize_text
from mediafactory.sources.urls import canonical_url

MIN_CHARS = 200


@register
class WebPageAdapter:
    key = "web"

    def validate(self, params: dict) -> dict:
        return {"url": http_url(params.get("url"))}

    def fetch(self, params: dict, ctx: FetchContext) -> list[RawItem]:
        url = params["url"]
        with translate_errors():
            if not ctx.fetcher.robots_allowed(url):
                raise AdapterError(f"robots.txt disallows fetching {url}", retryable=False)
            page = ctx.fetcher.get(url, headers={"Accept": "text/html,application/xhtml+xml"})
        title, text = extract_article(page.text)
        text = normalize_text(text)
        if len(text) < MIN_CHARS:
            raise AdapterError(f"{url}: no readable article text found", retryable=False)
        return [RawItem(external_id=canonical_url(page.url), url=page.url, title=title or url, text=text)]
