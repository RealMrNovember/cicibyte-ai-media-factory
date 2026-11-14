import pytest

from mediafactory.sources.feeds import FeedError, parse_feed

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>
<item><title>First &amp; best</title><link>https://example.com/1</link><guid>g1</guid>
<description>&lt;p&gt;Body one&lt;/p&gt;</description><pubDate>Sat, 14 Nov 2026 10:00:00 GMT</pubDate>
<author>a@example.com (Ann)</author></item>
<item><title>Second</title><link>https://example.com/2</link><description>Body two</description></item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><id>t3_abc</id><title>A story</title><link href="https://www.reddit.com/r/nosleep/comments/abc/x/"/>
<author><name>/u/writer</name></author><updated>2026-11-14T09:00:00+00:00</updated>
<content type="html">&lt;p&gt;It began at night.&lt;/p&gt;</content></entry></feed>"""


def test_parse_rss_items():
    entries = parse_feed(RSS)
    assert [e.title for e in entries] == ["First & best", "Second"]
    first = entries[0]
    assert first.id == "g1" and first.link == "https://example.com/1"
    assert "Body one" in first.summary_html
    assert first.published_at is not None and first.published_at.year == 2026


def test_parse_atom_entries():
    (e,) = parse_feed(ATOM)
    assert e.id == "t3_abc" and e.title == "A story"
    assert e.link == "https://www.reddit.com/r/nosleep/comments/abc/x/"
    assert e.author == "/u/writer" and "It began" in e.content_html


def test_billion_laughs_rejected():
    bomb = b"""<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;&lol;">
    <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;">]><rss><channel><item><title>&lol3;</title></item></channel></rss>"""
    with pytest.raises(FeedError):
        parse_feed(bomb)


def test_external_entity_rejected():
    xxe = b"""<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]>
    <rss><channel><item><title>&x;</title></item></channel></rss>"""
    with pytest.raises(FeedError):
        parse_feed(xxe)


def test_garbage_rejected():
    with pytest.raises(FeedError):
        parse_feed(b"<html><body>not a feed</body></html>")
    with pytest.raises(FeedError):
        parse_feed(b"\x00\x01 not xml")
