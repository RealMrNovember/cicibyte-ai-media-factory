import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from mediafactory import desktop


@pytest.fixture
def local(tmp_path, monkeypatch):
    monkeypatch.delenv("MF_SERVER_URL", raising=False)
    cfg = desktop.Config(tmp_path)
    cfg.set_server("http://127.0.0.1:9")  # nothing listens there
    srv = ThreadingHTTPServer(("127.0.0.1", 0), desktop.make_handler(cfg))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", cfg
    srv.shutdown()


def test_panel_served_even_without_server(local):
    base, _ = local
    with urllib.request.urlopen(base + "/") as r:
        assert b"<html" in r.read().lower()


def test_api_reports_unreachable_server(local):
    base, _ = local
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(base + "/api/health")
    assert e.value.code == 502 and e.value.headers["X-MF-Desktop"] == "1"


def test_server_address_saved_from_settings(local, tmp_path):
    base, cfg = local
    req = urllib.request.Request(
        base + "/desktop/config", method="POST", data=json.dumps({"server_url": "mediafactory:8080"}).encode(),
        headers={"Content-Type": "application/json", "X-MF-Client": "panel"},
    )  # fmt: skip
    with urllib.request.urlopen(req) as r:
        assert json.loads(r.read())["server_url"] == "http://mediafactory:8080"
    assert json.loads((tmp_path / "config.json").read_text())["server_url"] == "http://mediafactory:8080"


def test_static_path_traversal_falls_back_to_index(local):
    base, _ = local
    with urllib.request.urlopen(base + "/..%2F..%2Fpyproject.toml") as r:
        assert b"<html" in r.read().lower()
