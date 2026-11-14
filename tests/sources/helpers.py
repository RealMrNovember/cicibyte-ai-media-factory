import socket

import httpx

from mediafactory.core.net import SafeFetcher


def public_resolver(host, port, *args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port or 0))]


def make_fetcher(handler) -> SafeFetcher:
    return SafeFetcher(transport=httpx.MockTransport(handler), resolver=public_resolver, sleep=lambda s: None)


LONG = "The basement light flickered every night at exactly three. " * 12


def reddit_atom(entries):
    """entries: list of (id, title, body_html)."""
    body = "".join(
        f"""<entry><id>t3_{i}</id><title>{t}</title>
        <link href="https://www.reddit.com/r/nosleep/comments/{i}/slug/"/>
        <author><name>/u/writer{i}</name></author><updated>2026-11-14T09:00:00+00:00</updated>
        <content type="html">{b}</content></entry>"""
        for i, t, b in entries
    )
    return f'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">{body}</feed>'.encode()
