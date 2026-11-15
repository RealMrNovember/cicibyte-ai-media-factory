import json

import httpx
import pytest
import respx

from mediafactory.pipeline import stock

H = {"X-MF-Client": "1"}
HIT = {"id": "abc123", "title": "Parkour on rooftops", "thumbnail": "https://cdn.coverr.co/t.jpg", "duration": 12.5,
       "is_vertical": False, "aspect_ratio": "16:9",
       "urls": {"mp4": "https://cdn.coverr.co/v.mp4", "mp4_preview": "https://cdn.coverr.co/p.mp4",
                "mp4_download": "https://cdn.coverr.co/d.mp4"}}  # fmt: skip


@respx.mock
def test_coverr_search_sends_the_key_in_a_header_and_maps_hits():
    route = respx.get(f"{stock.COVERR}/videos").mock(return_value=httpx.Response(200, json={"hits": [HIT], "pages": 3, "page": 0}))
    out = stock.coverr_search("ck_secret", "parkour", page=0)
    req = route.calls[0].request
    assert req.headers["x-api-key"] == "ck_secret" and "ck_secret" not in str(req.url)
    assert dict(req.url.params) | {} == {"query": "parkour", "page": "0", "page_size": "24", "urls": "true"}
    assert out["pages"] == 3 and out["items"][0] == {"id": "abc123", "title": "Parkour on rooftops", "thumbnail": HIT["thumbnail"],
                                                    "preview": HIT["urls"]["mp4_preview"], "duration": 12.5, "vertical": False}


@respx.mock
def test_bad_key_is_a_clear_error():
    respx.get(f"{stock.COVERR}/videos").mock(return_value=httpx.Response(401, json={"message": "Unauthorized"}))
    with pytest.raises(stock.StockError, match="key"):
        stock.coverr_search("bad", "x")


@respx.mock
def test_coverr_import_downloads_into_the_library_with_licence(tmp_path):
    respx.get(f"{stock.COVERR}/videos/abc123").mock(return_value=httpx.Response(200, json=HIT))
    respx.get("https://cdn.coverr.co/d.mp4").mock(return_value=httpx.Response(200, content=b"\x00" * 5000))
    ping = respx.patch(f"{stock.COVERR}/videos/abc123/stats/downloads").mock(return_value=httpx.Response(204))
    clip = stock.coverr_import(tmp_path, "ck", "abc123", tags=["horror", "not-a-topic"])
    meta = json.loads(clip.with_suffix(clip.suffix + ".json").read_text(encoding="utf-8"))
    assert clip.name.startswith("coverr-parkour-on-rooftops") and clip.stat().st_size == 5000
    assert "Coverr" in meta["licence"] and meta["source"] == "https://coverr.co/videos/abc123" and meta["tags"] == ["horror"]
    assert ping.called


def test_mixkit_links_are_recognised():
    assert stock.mixkit_id("https://mixkit.co/free-stock-video/man-running-on-a-rooftop-34512/") == "34512"
    assert stock.mixkit_id("https://assets.mixkit.co/videos/34512/34512-720.mp4") == "34512"
    assert stock.mixkit_id("https://evil.example/34512.mp4") is None


@respx.mock
def test_mixkit_import_takes_the_best_available_size(tmp_path):
    respx.head("https://assets.mixkit.co/videos/34512/34512-1080.mp4").mock(return_value=httpx.Response(404))
    respx.head("https://assets.mixkit.co/videos/34512/34512-720.mp4").mock(return_value=httpx.Response(200))
    respx.get("https://assets.mixkit.co/videos/34512/34512-720.mp4").mock(return_value=httpx.Response(200, content=b"\x01" * 3000))
    clip = stock.mixkit_import(tmp_path, "https://mixkit.co/free-stock-video/man-running-on-a-rooftop-34512/", tags=["parkour"])
    meta = json.loads(clip.with_suffix(clip.suffix + ".json").read_text(encoding="utf-8"))
    assert clip.name.startswith("mixkit-man-running-on-a-rooftop") and "Mixkit" in meta["licence"]


def test_downloads_are_capped(tmp_path, monkeypatch):
    monkeypatch.setattr(stock, "MAX_BYTES", 1000)
    with respx.mock:
        respx.get("https://cdn.coverr.co/big.mp4").mock(return_value=httpx.Response(200, content=b"\x00" * 5000))
        with pytest.raises(stock.StockError, match="too large"):
            stock._download("https://cdn.coverr.co/big.mp4", tmp_path / "x.mp4")
    assert not (tmp_path / "x.mp4").exists()


def test_only_known_hosts_are_downloaded(tmp_path):
    with pytest.raises(stock.StockError, match="host"):
        stock._download("https://127.0.0.1/secret.mp4", tmp_path / "x.mp4")


def test_key_is_stored_encrypted_and_never_returned(client, db):
    r = client.put("/api/stock/coverr-key", json={"key": "ck_live_abcdef123456"}, headers=H)
    assert r.status_code == 200 and r.json() == {"coverr": True}
    assert "abcdef" not in json.dumps(client.get("/api/stock", headers=H).json())
    assert stock.coverr_key(db) == "ck_live_abcdef123456"


def test_search_without_key_is_409(client):
    assert client.get("/api/stock/coverr?q=fog", headers=H).status_code == 409
