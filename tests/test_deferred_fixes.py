import httpx
import pytest

from mediafactory.ai.router import TaskNotConfigured
from mediafactory.core.net import SafeFetcher, is_public_ip
from mediafactory.core.redact import redact

H = {"X-MF-Client": "1"}


@pytest.mark.parametrize("addr", [
    "2002:c0a8:0101::1",                 # 6to4 wrapping 192.168.1.1
    "2001:0:4136:e378:8000:63bf:f5ff:fefe",  # Teredo whose client is 10.0.0.1 (obfuscated)
    "64:ff9b::a00:1",                    # NAT64 well-known prefix wrapping 10.0.0.1
    "64:ff9b::7f00:1",                   # NAT64 wrapping 127.0.0.1
])  # fmt: skip
def test_private_ipv4_inside_ipv6_is_refused(addr):
    assert not is_public_ip(addr)


def test_public_ipv4_inside_nat64_and_ordinary_ipv6_still_pass():
    assert is_public_ip("64:ff9b::808:808")  # 8.8.8.8
    assert is_public_ip("2606:4700:4700::1111")


def test_credentials_are_not_sent_to_another_host_after_a_redirect():
    seen = []

    def handler(request):
        seen.append((request.url.host, request.headers.get("authorization"), request.headers.get("cookie")))
        if request.url.host == "a.example":
            return httpx.Response(302, headers={"location": "https://b.example/x"})
        return httpx.Response(200, text="ok")

    f = SafeFetcher(resolver=lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 443))], min_interval_s=0,
                    transport=httpx.MockTransport(handler))  # fmt: skip
    f.get("https://a.example/start", headers={"Authorization": "Bearer s3cret", "Cookie": "c=1"})
    assert seen[0][1] == "Bearer s3cret" and seen[1] == ("b.example", None, None)


def test_passwords_in_urls_are_masked():
    assert redact("connect http://bob:hunter2@10.0.0.5:8080/v1 failed") == "connect http://bob:****@10.0.0.5:8080/v1 failed"
    assert redact("https://example.com/a@b") == "https://example.com/a@b"


def test_missing_task_route_is_not_retried():
    assert getattr(TaskNotConfigured("script"), "retryable", True) is False


def test_very_long_feed_urls_are_kept_without_url(db):
    from mediafactory.sources.adapters.base import RawItem
    from mediafactory.sources.ingest import store_items

    text = "A long enough story about the attic and what lived in it. " * 10
    res = store_items(db, None, [RawItem(external_id="x", url="https://example.com/" + "a" * 2100, title="t", text=text)],
                      source_type="rss")
    assert len(res.item_ids) == 1


def test_angle_brackets_in_uploaded_text_survive(client):
    body = "Bir gece <kapı> çaldı. " * 30
    r = client.post("/api/items/manual/upload", files={"file": ("story.txt", body.encode(), "text/plain")}, data={"title": "Kapı"},
                    headers=H)  # fmt: skip
    assert r.status_code == 201, r.text
    item = client.get(f"/api/items/{r.json()['item']['id']}", headers=H).json()["item"]
    assert "<kapı>" in item["text"]


def test_atom_xhtml_content_is_read():
    from mediafactory.sources.feeds import parse_feed

    feed = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>t</title>
      <entry><id>1</id><title>Story</title><link href="https://example.com/1"/>
        <content type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml"><p>The attic door <b>opened</b> at night.</p></div></content>
      </entry></feed>"""
    entry = parse_feed(feed)[0]
    assert "The attic door" in entry.content_html and "opened" in entry.content_html
