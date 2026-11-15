"""RSS 2.0 / Atom parsing with defusedxml (no DTDs, no entity expansion, no external entities)."""

from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from xml.etree.ElementTree import Element, ParseError

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring

ATOM = "{http://www.w3.org/2005/Atom}"
CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}"
DC = "{http://purl.org/dc/elements/1.1/}"
RSS1 = "{http://purl.org/rss/1.0/}"


class FeedError(Exception):
    pass


@dataclass
class FeedEntry:
    id: str
    link: str | None
    title: str
    author: str | None
    published_at: datetime | None
    content_html: str
    summary_html: str


def _text(el: Element | None, path: str) -> str:
    if el is None:
        return ""
    found = el.find(path)
    if found is None:
        return ""
    if found.get("type") == "xhtml" or (not (found.text or "").strip() and len(found)):
        # Atom type="xhtml": the content is child elements (a <div>), not text. Give it back as markup.
        from xml.etree.ElementTree import tostring

        return "".join(tostring(child, encoding="unicode") for child in found).strip()
    return (found.text or "").strip()


def _date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _rss_items(root: Element, ns: str = "") -> list[FeedEntry]:
    """RSS 2.0 (no namespace) or RSS 1.0/RDF (elements in the RSS1 namespace)."""
    out = []
    for item in root.iter(f"{ns}item"):
        link = _text(item, f"{ns}link") or None
        out.append(
            FeedEntry(
                id=_text(item, "guid") or item.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about") or link
                or _text(item, f"{ns}title"),
                link=link,
                title=_text(item, f"{ns}title"),
                author=_text(item, "author") or _text(item, f"{DC}creator") or None,
                published_at=_date(_text(item, "pubDate") or _text(item, f"{DC}date")),
                content_html=_text(item, f"{CONTENT_NS}encoded"),
                summary_html=_text(item, f"{ns}description"),
            )
        )
    return out


def _atom_entries(root: Element) -> list[FeedEntry]:
    out = []
    for entry in root.iter(f"{ATOM}entry"):
        link = None
        for el in entry.findall(f"{ATOM}link"):
            if el.get("rel", "alternate") == "alternate" and el.get("href"):
                link = el.get("href")
                break
        out.append(
            FeedEntry(
                id=_text(entry, f"{ATOM}id") or link or _text(entry, f"{ATOM}title"),
                link=link,
                title=_text(entry, f"{ATOM}title"),
                author=_text(entry, f"{ATOM}author/{ATOM}name") or None,
                published_at=_date(_text(entry, f"{ATOM}published") or _text(entry, f"{ATOM}updated")),
                content_html=_text(entry, f"{ATOM}content"),
                summary_html=_text(entry, f"{ATOM}summary"),
            )
        )
    return out


def parse_feed(content: bytes) -> list[FeedEntry]:
    try:
        root = fromstring(content, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except (DefusedXmlException, ParseError, ValueError) as exc:
        raise FeedError(f"invalid or unsafe feed XML: {type(exc).__name__}") from None
    tag = root.tag
    if tag == "rss":
        return _rss_items(root)
    if tag.endswith("RDF"):
        return _rss_items(root, RSS1) or _rss_items(root)
    if tag == f"{ATOM}feed":
        return _atom_entries(root)
    raise FeedError(f"not an RSS/Atom feed (root element <{tag}>)")
