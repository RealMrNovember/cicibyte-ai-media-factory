import io
from html import escape

import httpx
import pytest
from sqlalchemy import select

from mediafactory.db.models import AuditLog, SourceItem, SourceRightsRecord
from tests.helpers import csrf_headers, login
from tests.sources.helpers import LONG, make_fetcher, reddit_atom


def text_pdf(text: str) -> bytes:
    """A minimal one-page PDF with real text (built by hand, so no extra test dependency)."""
    stream = f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = io.BytesIO(), []
    out.write(b"%PDF-1.4\n")
    for i, body in enumerate(objs, 1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return out.getvalue()


def encrypted_pdf() -> bytes:
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(text_pdf("secret story " * 10))))
    writer.encrypt("pw")
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def docx_bytes(text: str) -> bytes:
    from docx import Document

    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@pytest.fixture
def h(client, make_user, app):
    make_user()
    login(client)
    return csrf_headers(client)


def use_fetcher(app, handler):
    from mediafactory.api.routes.items import get_fetcher

    app.dependency_overrides[get_fetcher] = lambda: make_fetcher(handler)


def test_manual_text_created_with_chosen_rights(client, h, db):
    r = client.post(
        "/api/items/manual", json={"title": "My tale", "text": LONG, "rights_status": "user_owned", "note": "mine"},
        headers=h,
    )  # fmt: skip
    assert r.status_code == 201
    item = db.get(SourceItem, r.json()["item"]["id"])
    assert item.source_type == "manual" and item.rights_status == "user_owned" and item.title == "My tale"
    rec = db.scalar(select(SourceRightsRecord).where(SourceRightsRecord.item_id == item.id))
    assert rec.actor_id is not None and rec.to_status == "user_owned"
    assert db.scalar(select(AuditLog).where(AuditLog.action == "item.manual")) is not None


def test_manual_requires_text_or_url_422(client, h):
    assert client.post("/api/items/manual", json={"rights_status": "unknown"}, headers=h).status_code == 422


def test_manual_text_too_short_422(client, h):
    r = client.post("/api/items/manual", json={"text": "hi", "rights_status": "unknown"}, headers=h)
    assert r.status_code == 422


def test_manual_url_uses_safe_fetcher(client, h, app):
    use_fetcher(app, lambda r: httpx.Response(200, text="x"))
    r = client.post("/api/items/manual", json={"url": "http://127.0.0.1/admin", "rights_status": "unknown"}, headers=h)
    assert r.status_code == 422 and "non-public" in r.json()["detail"]


def test_manual_web_url(client, h, app, db):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text=f"<title>Web tale</title><p>{LONG}</p>")

    use_fetcher(app, handler)
    r = client.post("/api/items/manual", json={"url": "https://example.com/tale", "rights_status": "licensed"}, headers=h)
    assert r.status_code == 201
    assert r.json()["item"]["canonical_url"] == "https://example.com/tale"


def test_manual_reddit_post_url_reads_rss(client, h, app):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, content=reddit_atom([("zz9", "Reddit tale", escape(f"<p>{LONG}</p>"))]))

    use_fetcher(app, handler)
    r = client.post(
        "/api/items/manual",
        json={"url": "https://old.reddit.com/r/nosleep/comments/zz9/slug/?utm_source=x", "rights_status": "unknown"},
        headers=h,
    )
    assert r.status_code == 201
    assert seen == ["https://www.reddit.com/r/nosleep/comments/zz9/.rss"]
    assert r.json()["item"]["title"] == "Reddit tale"


@pytest.mark.parametrize(
    "name,data,expect",
    [
        ("story.txt", LONG.encode("utf-8"), "basement light"),
        ("story.md", ("# Title\n\n" + LONG).encode("utf-8"), "basement light"),
        ("story.docx", docx_bytes(LONG), "basement light"),
        ("story.pdf", text_pdf("The basement light flickered every night at exactly three o clock " * 2), "basement light"),
    ],
)
def test_upload_txt_md_docx_pdf(client, h, db, name, data, expect):
    r = client.post(
        "/api/items/manual/upload", files={"file": (name, data)}, data={"rights_status": "user_owned"}, headers=h
    )
    assert r.status_code == 201, r.text
    assert expect in db.get(SourceItem, r.json()["item"]["id"]).normalized_text


def test_encrypted_pdf_422(client, h):
    r = client.post("/api/items/manual/upload", files={"file": ("x.pdf", encrypted_pdf())}, data={"rights_status": "unknown"}, headers=h)
    assert r.status_code == 422 and "encrypted" in r.json()["detail"].lower()


def test_corrupt_docx_422(client, h):
    r = client.post("/api/items/manual/upload", files={"file": ("x.docx", b"PK\x03\x04broken")}, data={"rights_status": "unknown"}, headers=h)
    assert r.status_code == 422


def test_unsupported_type_422(client, h):
    r = client.post("/api/items/manual/upload", files={"file": ("x.exe", b"MZ")}, data={"rights_status": "unknown"}, headers=h)
    assert r.status_code == 422


def test_oversized_upload_422(client, h):
    big = b"a" * (10 * 1024 * 1024 + 1)
    r = client.post("/api/items/manual/upload", files={"file": ("big.txt", big)}, data={"rights_status": "unknown"}, headers=h)
    assert r.status_code == 422 and "10 MB" in r.json()["detail"]


def test_duplicate_manual_returns_existing(client, h):
    body = {"text": LONG, "rights_status": "unknown"}
    first = client.post("/api/items/manual", json=body, headers=h).json()
    r = client.post("/api/items/manual", json=body, headers=h)
    assert r.status_code == 200 and r.json()["duplicate"] is True and r.json()["item"]["id"] == first["item"]["id"]


def test_invalid_rights_status_422(client, h):
    assert client.post("/api/items/manual", json={"text": LONG, "rights_status": "mine"}, headers=h).status_code == 422
