"""Desktop app: a native window onto a Media Factory server.

All production (database, AI, voice, captions, rendering, scheduling) runs on the server; this app only
shows its panel. The server address is asked on first start and kept in
%LOCALAPPDATA%\\CiciByteMediaFactory\\config.json (or ~/.cicibyte-media-factory/config.json).
Powered by CiciByte Technology — https://cicibyte.com
"""

import json
import os
import urllib.request
from pathlib import Path

APP_NAME = "CiciByte AI Media Factory"
DEFAULT_SERVER = "http://mediafactory:8080"


def app_home() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    home = Path(base) / "CiciByteMediaFactory" if base else Path.home() / ".cicibyte-media-factory"
    home.mkdir(parents=True, exist_ok=True)
    return home


def load_config(home: Path) -> dict:
    path = home / "config.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(home: Path, cfg: dict) -> None:
    (home / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def normalize(url: str) -> str:
    url = url.strip().rstrip("/")
    if url and "://" not in url:
        url = "http://" + url
    return url


def reachable(url: str, timeout: float = 4.0) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/api/health", timeout=timeout) as r:  # noqa: S310 (user-chosen server)
            return r.status == 200 and json.loads(r.read()).get("status") == "ok"
    except Exception:
        return False


SETUP_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;background:#0b0b0e;color:#ececf1;font:15px/1.5 "Segoe UI",system-ui,sans-serif;display:grid;place-items:center;height:100vh}
.c{background:#131318;border:1px solid #26262f;border-radius:14px;padding:28px;width:min(460px,92vw)}
h1{font-size:20px;margin:0 0 4px}p{color:#8e8e9c;margin:0 0 18px;font-size:14px}
input{width:100%;box-sizing:border-box;background:#0b0b0e;border:1px solid #26262f;border-radius:9px;padding:10px 12px;color:inherit;font:inherit}
button{margin-top:14px;width:100%;background:#c9a96e;color:#1a1408;border:0;border-radius:9px;padding:10px;font-weight:600;font:inherit;cursor:pointer}
#e{color:#e0645c;font-size:13px;min-height:18px;margin-top:10px}small{display:block;margin-top:18px;color:#8e8e9c;font-size:12px}
a{color:#c9a96e}</style></head><body><div class="c">
<h1>CiciByte AI Media Factory</h1>
<p>Sunucu adresi / Server address — üretim bu sunucuda çalışır.</p>
<input id="u" value="__URL__" placeholder="http://mediafactory:8080" autofocus>
<button onclick="go()">Bağlan / Connect</button><div id="e">__ERR__</div>
<small>Powered by CiciByte Technology · cicibyte.com</small></div>
<script>
async function go(){document.getElementById('e').textContent='…';
 const r=await window.pywebview.api.connect(document.getElementById('u').value);
 if(r!==true)document.getElementById('e').textContent=r;}
document.getElementById('u').addEventListener('keydown',e=>{if(e.key==='Enter')go()});
</script></body></html>"""


class Api:
    def __init__(self, home: Path, cfg: dict):
        self.home, self.cfg, self.window = home, cfg, None

    def connect(self, url: str):
        url = normalize(url)
        if not reachable(url):
            return f"Sunucuya ulaşılamadı / Cannot reach {url}"
        self.cfg["server_url"] = url
        save_config(self.home, self.cfg)
        self.window.load_url(url + "/")
        return True


def setup_page(url: str, err: str = "") -> str:
    esc = lambda s: s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")  # noqa: E731
    return SETUP_HTML.replace("__URL__", esc(url)).replace("__ERR__", esc(err))


def main() -> None:
    import webview

    home = app_home()
    cfg = load_config(home)
    url = normalize(os.environ.get("MF_SERVER_URL") or cfg.get("server_url") or DEFAULT_SERVER)
    api = Api(home, cfg)
    if reachable(url):
        window = webview.create_window(APP_NAME, url + "/", js_api=api, width=1320, height=880, min_size=(420, 600))
    else:
        err = "" if not cfg.get("server_url") else f"Sunucuya ulaşılamadı / Cannot reach {url}"
        window = webview.create_window(APP_NAME, html=setup_page(url, err), js_api=api, width=1320, height=880,
                                       min_size=(420, 600))  # fmt: skip
    api.window = window
    webview.start(private_mode=False, storage_path=str(home / "webview"))


if __name__ == "__main__":
    main()
