from mediafactory.sources.urls import canonical_url


def test_canonical_url_strips_tracking():
    url = "HTTPS://WWW.Example.com/Story/?utm_source=x&b=2&a=1&fbclid=z#comments"
    assert canonical_url(url) == "https://example.com/Story?a=1&b=2"


def test_trailing_slash_removed_root_kept():
    assert canonical_url("https://example.com/") == "https://example.com/"
    assert canonical_url("https://example.com/a/") == "https://example.com/a"


def test_canonical_reddit_variants_equal():
    a = canonical_url("https://old.reddit.com/r/nosleep/comments/abc123/the_title/?utm_source=share")
    b = canonical_url("https://www.reddit.com/r/nosleep/comments/abc123")
    c = canonical_url("https://new.reddit.com/r/NoSleep/comments/abc123/other_slug/")
    assert a == b == "https://reddit.com/r/nosleep/comments/abc123"
    assert c == a
