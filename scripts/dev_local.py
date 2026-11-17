"""Run the desktop app's local mode without a window: engine + the app's local panel server.

Usage: python scripts/dev_local.py [--home DIR] [--port 8095]   then open http://127.0.0.1:8095/
"""

import argparse
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from mediafactory import desktop

ap = argparse.ArgumentParser()
ap.add_argument("--home", default=str(Path.home() / ".mf-dev-local"))
ap.add_argument("--port", type=int, default=8095)
args = ap.parse_args()
home = Path(args.home)
home.mkdir(parents=True, exist_ok=True)
desktop.sys.platform = "win32" if sys.platform == "win32" else desktop.sys.platform
cfg = desktop.Config(home)
cfg.data["mode"] = "local"
shutdown = desktop._start_engine(cfg)
server = ThreadingHTTPServer(("127.0.0.1", args.port), desktop.make_handler(cfg))
print(f"panel: http://127.0.0.1:{args.port}/  (data in {home})", flush=True)
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    shutdown()
    server.shutdown()
