# Adapted from purffle-shorts (MIT, Copyright (c) 2025 Purffle), commit 514fd2547227b98d951dfc1489fc8c7ce72f1b68
"""Text cleanup, hashing and readable-article extraction for source content."""

import hashlib
import html
import re
import unicodedata
from html.parser import HTMLParser

_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")
_REDDIT_SIGNATURE = re.compile(r"\s*submitted by\s+/u/\S+.*$", re.IGNORECASE | re.DOTALL)


def strip_html(text: str) -> str:
    return _SPACE.sub(" ", html.unescape(_TAG.sub(" ", text or ""))).strip()


def normalize_text(text: str) -> str:
    cleaned = _REDDIT_SIGNATURE.sub("", strip_html(text))
    return unicodedata.normalize("NFC", cleaned).strip()


def content_hash(normalized: str) -> str:
    key = _SPACE.sub(" ", normalized.casefold()).strip()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class _TextExtractor(HTMLParser):
    """Readable text from an article page: headings, paragraphs and list items, minus navigation."""

    SKIP = {"script", "style", "nav", "footer", "header", "aside", "form", "noscript", "svg", "button"}
    KEEP = {"p", "h1", "h2", "h3", "li", "blockquote"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title = ""
        self.meta_title = ""
        self._skip = 0
        self._keep = 0
        self._in_title = False
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in self.KEEP:
            self._keep += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            a = dict(attrs)
            if a.get("property") == "og:title" and a.get("content"):
                self.meta_title = a["content"]

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag in self.KEEP and self._keep:
            self._keep -= 1
            text = _SPACE.sub(" ", "".join(self._buf)).strip()
            self._buf = []
            if text and not self._skip and (len(text) > 30 or tag.startswith("h")):
                self.parts.append(text)
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._keep and not self._skip:
            self._buf.append(data)


def extract_article(page: str) -> tuple[str, str]:
    """(title, text) from an HTML page."""
    parser = _TextExtractor()
    parser.feed(page)
    title = (parser.meta_title or parser.title).strip()
    title = re.split(r"\s+[|–—-]\s+", title)[0].strip() if title else ""
    return title, "\n".join(dict.fromkeys(t for t in parser.parts if t))
