import hashlib
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from mediafactory import desktop, desktop_update as du

REL = "https://github.com/RealMrNovember/cicibyte-ai-media-factory/releases/download/v0.3.0/"


def release(tag="v0.3.0", assets=("CiciByteMediaFactory-Setup-0.3.0.exe", "CiciByteMediaFactory-Setup-0.3.0.exe.sha256")):
    return {"tag_name": tag, "html_url": "https://github.com/x/releases/tag/" + tag, "body": "notes",
            "assets": [{"name": n, "browser_download_url": REL + n, "size": 10} for n in assets]}  # fmt: skip


def test_version_compare():
    assert du.newer("0.3.0", "0.2.0") and du.newer("v1.0.0", "0.9.9") and du.newer("0.10.0", "0.9.0")
    assert not du.newer("0.2.0", "0.2.0") and not du.newer("0.1.9", "0.2.0") and not du.newer("garbage", "0.2.0")


def test_pick_update_from_release():
    info = du.pick_update(release(), current="0.2.0")
    assert info["version"] == "0.3.0" and info["installer"].endswith(".exe") and info["sha256_url"].endswith(".sha256")
    assert du.pick_update(release(tag="v0.2.0"), current="0.2.0") is None
    assert du.pick_update(release(assets=("notes.txt",)), current="0.2.0") is None  # no installer
    assert du.pick_update(release(assets=("CiciByteMediaFactory-Setup-0.3.0.exe",)), current="0.2.0") is None  # no checksum


def test_only_this_repositorys_release_urls_are_trusted():
    bad = release()
    bad["assets"][0]["browser_download_url"] = "https://evil.example/Setup.exe"
    assert du.pick_update(bad, current="0.2.0") is None


def test_download_verifies_checksum(tmp_path, monkeypatch):
    payload = b"installer-bytes"
    digest = hashlib.sha256(payload).hexdigest()
    files = {REL + "a.exe": payload, REL + "a.exe.sha256": f"{digest}  a.exe\n".encode(), REL + "bad.sha256": b"0" * 64}
    monkeypatch.setattr(du, "_fetch", lambda url, timeout=60: files[url])
    path = du.download({"installer": REL + "a.exe", "sha256_url": REL + "a.exe.sha256", "version": "0.3.0"}, tmp_path)
    assert path.read_bytes() == payload
    with pytest.raises(du.UpdateError):
        du.download({"installer": REL + "a.exe", "sha256_url": REL + "bad.sha256", "version": "0.3.0"}, tmp_path)


def test_desktop_config_reports_update(tmp_path, monkeypatch):
    monkeypatch.delenv("MF_SERVER_URL", raising=False)
    cfg = desktop.Config(tmp_path)
    cfg.set_server("http://127.0.0.1:9")
    cfg.update = {"version": "0.3.0", "installer": REL + "x.exe", "sha256_url": REL + "x.exe.sha256", "notes": "n"}
    srv = ThreadingHTTPServer(("127.0.0.1", 0), desktop.make_handler(cfg))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}/desktop/config") as r:
            data = json.loads(r.read())
        assert data["app_version"] and data["update"]["version"] == "0.3.0"
    finally:
        srv.shutdown()
