from mediafactory.sources.text import content_hash, extract_article, normalize_text, strip_html


def test_strip_html_and_entities():
    assert strip_html("<p>Tom &amp; Jerry<br/>said&nbsp;hi</p>") == "Tom & Jerry said hi"


def test_normalize_removes_reddit_signature():
    raw = "<div><p>It was dark.</p></div> submitted by /u/someone [link] [comments]"
    assert normalize_text(raw) == "It was dark."


def test_normalize_unicode_nfc():
    assert normalize_text("Café") == "Café"


def test_hash_ignores_case_and_whitespace():
    assert content_hash(normalize_text("Hello   World")) == content_hash(normalize_text("hello world"))
    assert content_hash("a") != content_hash("b")


def test_extract_article_skips_nav():
    html = """<html><head><title>Ghost Story | Site</title></head><body>
    <nav><p>Home About Contact links that are long enough to count</p></nav>
    <article><h1>The House</h1><p>The old house at the end of the street was never empty at night.</p></article>
    <footer><p>Copyright footer text that is long enough to be counted</p></footer></body></html>"""
    title, text = extract_article(html)
    assert title == "Ghost Story"
    assert "never empty" in text and "Home About" not in text and "Copyright" not in text
