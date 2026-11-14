"""Local development setup: AI provider + script route + a reddit_rss source with fresh items.

Usage (from the repo root, test Postgres running):
    MF_DATABASE_URL=postgresql+psycopg://mf:mf@127.0.0.1:55432/mf_dev MF_SECRET_KEY=... \
    python scripts/dev_setup.py --router-url http://ai-router:20128/v1 --router-key-file .secrets/9router.key
"""

import argparse
from pathlib import Path

from sqlalchemy import select

from mediafactory.core.crypto import encrypt
from mediafactory.core.net import SafeFetcher
from mediafactory.db.models import AIProvider, AITaskRoute, SourceConnector, SourceItem
from mediafactory.db.session import session_scope
from mediafactory.sources.poller import run_source


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--router-url", required=True)
    p.add_argument("--router-key-file", required=True)
    p.add_argument("--model", default="mf-senaryo")
    p.add_argument("--subreddit", default="nosleep")
    a = p.parse_args()
    key = Path(a.router_key_file).read_text(encoding="utf-8").strip()

    with session_scope() as s:
        prov = s.scalar(select(AIProvider).where(AIProvider.name == "router"))
        if prov is None:
            prov = AIProvider(name="router", base_url=a.router_url, locality="remote", timeout_s=300)
            s.add(prov)
        prov.base_url, prov.api_key_enc, prov.enabled = a.router_url, encrypt(key), True
        s.flush()
        for task, model in (("script", a.model), ("classify", "mf-siniflandir")):
            route = s.scalar(select(AITaskRoute).where(AITaskRoute.task == task)) or AITaskRoute(task=task)
            route.steps, route.rounds, route.retry_delay_s = [{"provider_id": prov.id, "model": model}], 3, 3.0
            s.add(route)
        src = s.scalar(select(SourceConnector).where(SourceConnector.name == f"r/{a.subreddit}"))
        if src is None:
            src = SourceConnector(name=f"r/{a.subreddit}", adapter="reddit_rss",
                                  params={"subreddit": a.subreddit, "sort": "top", "time": "week", "min_chars": 400,
                                          "max_items": 15, "include_nsfw": False})  # fmt: skip
            s.add(src)
            s.flush()
        result = run_source(s, src, fetcher=SafeFetcher())
        print("collect:", result.as_dict())
        for item in s.scalars(select(SourceItem).order_by(SourceItem.id.desc()).limit(5)):
            print(f"  item {item.id}: {item.title[:80]} ({len(item.normalized_text)} chars)")


if __name__ == "__main__":
    main()
