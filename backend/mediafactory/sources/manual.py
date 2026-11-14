"""Manual intake: pasted text, a URL (web page or Reddit post) or an uploaded .txt/.md/.pdf/.docx file."""

import io
import re
import zipfile

from mediafactory.core.net import FetchError, SafeFetcher
from mediafactory.sources.adapters import AdapterError, FetchContext, RawItem, get_adapter
from mediafactory.sources.adapters.reddit_rss import clean_author
from mediafactory.sources.feeds import FeedError, parse_feed
from mediafactory.sources.text import normalize_text, strip_html

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = (".txt", ".md", ".pdf", ".docx")
REDDIT_POST = re.compile(
    r"^https?://(?:www\.|old\.|new\.|np\.|m\.)?reddit\.com/r/([A-Za-z0-9_]+)/comments/([A-Za-z0-9]+)", re.IGNORECASE
)


class ManualInputError(Exception):
    """User-fixable problem with manual input; shown as HTTP 422."""


def extract_file_text(filename: str, data: bytes) -> str:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ManualInputError("file is larger than 10 MB")
    name = filename.lower()
    if not name.endswith(ALLOWED_EXTENSIONS):
        raise ManualInputError(f"unsupported file type; use one of {', '.join(ALLOWED_EXTENSIONS)}")
    if name.endswith((".txt", ".md")):
        return data.decode("utf-8", errors="replace")
    if name.endswith(".pdf"):
        return _pdf_text(data)
    return _docx_text(data)


def _pdf_text(data: bytes) -> str:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ManualInputError("the PDF is encrypted; remove the password and upload it again")
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except ManualInputError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError, OSError) as exc:
        raise ManualInputError(f"the PDF could not be read ({type(exc).__name__})") from None


def _docx_text(data: bytes) -> str:
    from docx import Document

    try:
        doc = Document(io.BytesIO(data))
    except (zipfile.BadZipFile, KeyError, ValueError, OSError) as exc:
        raise ManualInputError(f"the DOCX file could not be read ({type(exc).__name__})") from None
    except Exception as exc:  # python-docx raises its own PackageNotFoundError subclasses
        raise ManualInputError(f"the DOCX file could not be read ({type(exc).__name__})") from None
    return "\n".join(p.text for p in doc.paragraphs)


def fetch_url_item(url: str, fetcher: SafeFetcher) -> RawItem:
    """Fetch one item from a URL: a Reddit post via its .rss, anything else via the web adapter."""
    m = REDDIT_POST.match(url.strip())
    try:
        if m:
            feed = fetcher.get(f"https://www.reddit.com/r/{m.group(1)}/comments/{m.group(2)}/.rss")
            entries = parse_feed(feed.content)
            if not entries:
                raise ManualInputError("Reddit returned no post for that link")
            e = entries[0]
            return RawItem(
                external_id=e.id,
                url=e.link or url,
                title=strip_html(e.title),
                text=normalize_text(e.content_html or e.summary_html),
                author=clean_author(e.author),
                published_at=e.published_at,
            )
        adapter = get_adapter("web")
        return adapter.fetch(adapter.validate({"url": url}), FetchContext(fetcher=fetcher))[0]
    except (FetchError, AdapterError, FeedError, ValueError) as exc:
        raise ManualInputError(str(exc)) from None
