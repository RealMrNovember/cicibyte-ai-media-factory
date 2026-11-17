"""Manual check: do pgserver's PostgreSQL binaries start here, take our migrations, and stop cleanly?

We use pgserver only as a carrier of the PostgreSQL binaries and drive initdb/pg_ctl ourselves (explicit port,
fast stop, no atexit magic). Usage: python scripts/spike_pgserver.py
"""

import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psycopg
from pgserver._commands import POSTGRES_BIN_PATH

BIN = Path(POSTGRES_BIN_PATH)
NOWIN = 0x08000000 if os.name == "nt" else 0

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    pgdata = Path(tmp) / "pg"
    t0 = time.monotonic()
    subprocess.run([BIN / "initdb", "-D", pgdata, "-U", "postgres", "-A", "trust", "-E", "UTF8", "--locale=C"],
                   check=True, capture_output=True, creationflags=NOWIN)
    print(f"initdb {time.monotonic() - t0:.1f}s")
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    t0 = time.monotonic()
    subprocess.run([BIN / "pg_ctl", "-D", pgdata, "-l", pgdata / "server.log", "-w", "-o", f"-h 127.0.0.1 -p {port}", "start"],
                   check=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   creationflags=NOWIN)  # no pipes: postgres inherits them and pg_ctl would never return
    print(f"start {time.monotonic() - t0:.1f}s on {port}")
    uri = f"postgresql://postgres@127.0.0.1:{port}/postgres"
    try:
        with psycopg.connect(uri) as conn:
            print(conn.execute("select version()").fetchone()[0][:40])
        env = {**os.environ, "MF_DATABASE_URL": uri.replace("postgresql://", "postgresql+psycopg://", 1),
               "MF_SECRET_KEY": secrets.token_urlsafe(48), "MF_DATA_DIR": str(Path(tmp) / "data")}
        r = subprocess.run([sys.executable, "-c", "from mediafactory.cli import app; app()", "migrate"], env=env, capture_output=True, text=True)
        print("migrate exit", r.returncode, (r.stdout + r.stderr).strip()[-300:])
        with psycopg.connect(uri) as conn:
            print("alembic head:", conn.execute("select version_num from alembic_version").fetchone()[0])
    finally:
        t0 = time.monotonic()
        subprocess.run([BIN / "pg_ctl", "-D", pgdata, "-w", "-m", "fast", "stop"], check=True, capture_output=True, creationflags=NOWIN)
        print(f"stop {time.monotonic() - t0:.1f}s")
