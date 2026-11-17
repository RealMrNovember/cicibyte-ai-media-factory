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


def test_frameless_only_when_the_panel_has_a_title_bar(tmp_path, monkeypatch):
    # unreachable server -> the bundled panel decides (it has the title bar)
    assert desktop.panel_has_titlebar("http://127.0.0.1:9") is True
    monkeypatch.setattr(desktop, "WEB_DIR", tmp_path)
    (tmp_path / "app.js").write_text("// an old panel without a title bar", encoding="utf-8")
    assert desktop.panel_has_titlebar("http://127.0.0.1:9") is False


def test_js_api_exposes_only_its_methods():
    """pywebview publishes every public attribute of the js_api object to the page, recursively. A public
    reference to the window made it walk the native window forever: black, frozen window (v0.3.0)."""
    from mediafactory.desktop import JsApi

    api = JsApi()
    api.set_window(object())
    public_attrs = [k for k, v in vars(api).items() if not k.startswith("_")]
    assert public_attrs == []
    assert {"minimize", "toggle_maximize", "close", "size", "resize", "open_url"} <= {n for n in dir(api) if not n.startswith("_")}


def test_studio_fonts_are_bundled_with_the_panel():
    from mediafactory.desktop import WEB_DIR

    css = (WEB_DIR / "fonts" / "fonts.css").read_text(encoding="utf-8")
    assert "googleapis" not in (WEB_DIR / "index.html").read_text(encoding="utf-8")
    for family in ("Montserrat", "Bebas Neue", "Lato", "Open Sans", "Roboto"):
        assert f"font-family: '{family}'" in css
    for name in __import__("re").findall(r"url\(([^)]+\.woff2)\)", css):
        assert (WEB_DIR / "fonts" / name).stat().st_size > 1000


# ---------- local / remote mode (v0.5.0) ----------


def test_saved_server_keeps_old_installs_in_remote_mode(tmp_path, monkeypatch):
    monkeypatch.delenv("MF_SERVER_URL", raising=False)
    (tmp_path / "config.json").write_text(json.dumps({"server_url": "http://mediafactory:8080"}))
    cfg = desktop.Config(tmp_path)
    assert cfg.mode == "remote" and cfg.target_url == "http://mediafactory:8080"


def test_new_install_runs_locally_on_windows_and_has_no_built_in_server(tmp_path, monkeypatch):
    monkeypatch.delenv("MF_SERVER_URL", raising=False)
    monkeypatch.setattr(desktop.sys, "platform", "win32")
    cfg = desktop.Config(tmp_path)
    assert cfg.mode == "local" and cfg.server_url == ""
    cfg.engine_url = "http://127.0.0.1:5123"
    assert cfg.target_url == "http://127.0.0.1:5123"
    assert not hasattr(desktop, "DEFAULT_SERVER")


def test_new_install_elsewhere_is_remote_until_local_mode_ships(tmp_path, monkeypatch):
    monkeypatch.delenv("MF_SERVER_URL", raising=False)
    monkeypatch.setattr(desktop.sys, "platform", "linux")
    cfg = desktop.Config(tmp_path)
    assert cfg.mode == "remote" and cfg.server_url == "" and not desktop.local_supported()


def test_api_waits_while_the_local_engine_starts(tmp_path, monkeypatch):
    monkeypatch.delenv("MF_SERVER_URL", raising=False)
    monkeypatch.setattr(desktop.sys, "platform", "win32")
    cfg = desktop.Config(tmp_path)
    cfg.engine_state = {"state": "starting", "step": "migrate", "error": None}
    srv = ThreadingHTTPServer(("127.0.0.1", 0), desktop.make_handler(cfg))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(base + "/api/health")
        assert e.value.code == 503 and json.loads(e.value.read())["engine"]["step"] == "migrate"
        with urllib.request.urlopen(base + "/desktop/config") as r:
            conf = json.loads(r.read())
        assert conf["mode"] == "local" and conf["local_supported"] is True and conf["engine"]["state"] == "starting"
        req = urllib.request.Request(base + "/desktop/config", method="POST", data=json.dumps({"mode": "remote"}).encode(),
                                     headers={"X-MF-Client": "1", "Content-Type": "application/json"})
        with urllib.request.urlopen(req) as r:
            assert json.loads(r.read())["restart_required"] is True
        assert json.loads((tmp_path / "config.json").read_text())["mode"] == "remote"
    finally:
        srv.shutdown()


def test_focus_request_brings_the_window_forward(tmp_path, monkeypatch):
    monkeypatch.delenv("MF_SERVER_URL", raising=False)
    cfg = desktop.Config(tmp_path)
    seen = []
    cfg.on_focus = lambda: seen.append(1)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), desktop.make_handler(cfg))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}/__focus", method="POST", data=b"{}")
        with urllib.request.urlopen(req) as r:
            assert r.status == 200
        assert seen == [1]
    finally:
        srv.shutdown()


def test_entry_runs_engine_children_without_the_window(monkeypatch):
    import importlib.util
    from pathlib import Path

    from mediafactory import desktop_engine

    seen = []
    monkeypatch.setattr(desktop_engine, "child_main", lambda argv=None: seen.append("child"))
    monkeypatch.setattr(desktop, "main", lambda: seen.append("window"))
    spec = importlib.util.spec_from_file_location("entry", Path(__file__).parent.parent / "packaging" / "desktop_entry.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.run(["--engine", "worker"])
    mod.run([])
    assert seen == ["child", "window"]


# ---------- review fixes ----------


def test_an_older_install_without_a_saved_address_stays_on_its_server(tmp_path, monkeypatch):
    """v0.4 and older used a built-in default address and wrote config.json only for other settings."""
    monkeypatch.delenv("MF_SERVER_URL", raising=False)
    monkeypatch.setattr(desktop.sys, "platform", "win32")
    (tmp_path / "config.json").write_text(json.dumps({"notifications": True}))
    cfg = desktop.Config(tmp_path)
    assert cfg.mode == "remote" and cfg.server_url == desktop.LEGACY_SERVER


def test_switching_mode_waits_for_the_restart(tmp_path, monkeypatch):
    monkeypatch.delenv("MF_SERVER_URL", raising=False)
    monkeypatch.setattr(desktop.sys, "platform", "win32")
    cfg = desktop.Config(tmp_path)
    assert cfg.mode == "local"
    cfg.set_option("mode", "remote")
    assert cfg.mode == "local" and cfg.saved_mode == "remote"  # this session keeps running as it started


def test_requests_for_another_host_name_are_refused(local):
    """DNS rebinding: a web page whose name points at 127.0.0.1 must not use the app's API or panel."""
    base, _ = local
    port = base.rsplit(":", 1)[1]
    req = urllib.request.Request(base + "/desktop/config", headers={"Host": f"evil.example:{port}"})
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req)
    assert e.value.code == 403
    ok = urllib.request.Request(base + "/desktop/config", headers={"Host": f"localhost:{port}"})
    with urllib.request.urlopen(ok) as r:
        assert r.status == 200


def test_update_stops_the_engine_before_the_installer_starts(tmp_path, monkeypatch):
    from mediafactory import desktop_update

    order = []
    cfg = desktop.Config(tmp_path)
    cfg.update = {"version": "9.9.9", "installer": "https://example/x.exe"}
    cfg.shutdown = lambda: order.append("engine stopped")
    monkeypatch.setattr(desktop_update, "download", lambda upd, d: tmp_path / "x.exe")
    monkeypatch.setattr(desktop_update, "launch_installer", lambda path: order.append("installer"))
    monkeypatch.setattr(desktop.threading, "Timer", lambda s, fn: type("T", (), {"start": lambda self: None})())
    srv = ThreadingHTTPServer(("127.0.0.1", 0), desktop.make_handler(cfg))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}/desktop/update", method="POST", data=b"{}",
                                     headers={"X-MF-Client": "1"})
        urllib.request.urlopen(req).read()
    finally:
        srv.shutdown()
    assert order == ["engine stopped", "installer"]
