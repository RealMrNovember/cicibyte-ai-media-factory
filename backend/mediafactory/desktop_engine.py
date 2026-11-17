"""The production engine the desktop app runs on this computer ("local" mode).

Pieces, all bound to 127.0.0.1 and kept in the app's data folder:
- PostgreSQL (binaries shipped by the pgserver package; we drive initdb/pg_ctl ourselves),
- `mf migrate`, then two child processes of the same executable: the API and the worker.
The app runs as a single instance, so one window owns the engine: closing it stops everything.
The worker is asked to stop with a file (Windows has no gentle SIGTERM) and killed after a timeout.
"""

import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path

NO_WINDOW = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW: no console flashes for children
QUIET = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
HEALTH_TIMEOUT_S = 90
CHILDREN = ("api", "worker")


class EngineError(Exception):
    pass


def engine_dir(home: Path) -> Path:
    return Path(home) / "data"


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def secret_key(directory: Path) -> str:
    """The engine's MF_SECRET_KEY: made once, then reused (stored keys are encrypted with it)."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "engine.key"
    if path.is_file():
        key = path.read_text(encoding="utf-8").strip()
        if len(key) >= 32:
            return key
    key = secrets.token_urlsafe(48)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(key)
    return key


class SingleInstance:
    """An OS file lock: only one app window per user. The running one publishes a port to bring it forward."""

    def __init__(self, home: Path):
        self.home = Path(home)
        self.lock_path = self.home / "instance.lock"
        self.info_path = self.home / "instance.json"
        self._fd: int | None = None

    def acquire(self) -> bool:
        self.home.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return False
        self._fd = fd
        return True

    def publish(self, port: int) -> None:
        self.info_path.write_text(json.dumps({"port": port, "pid": os.getpid()}), encoding="utf-8")

    def focus_existing(self) -> bool:
        try:
            port = int(json.loads(self.info_path.read_text(encoding="utf-8"))["port"])
            req = urllib.request.Request(f"http://127.0.0.1:{port}/__focus", data=b"{}", method="POST")
            with urllib.request.urlopen(req, timeout=3) as r:  # noqa: S310 - our own loopback port
                return r.status == 200
        except (OSError, ValueError, KeyError):
            return False

    def release(self) -> None:
        if self._fd is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                os.lseek(self._fd, 0, 0)
                msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._fd, fcntl.LOCK_UN)
        finally:
            os.close(self._fd)
            self._fd = None


def pg_bin_dir() -> Path:
    from pgserver._commands import POSTGRES_BIN_PATH  # the PostgreSQL 16 binaries shipped in the package

    return Path(POSTGRES_BIN_PATH)


class EngineDB:
    """A private PostgreSQL in <data>/pg on a free 127.0.0.1 port, with a random password (not "trust":
    other programs and users on this computer must not get a superuser)."""

    def __init__(self, root: Path, *, bin_dir: Path | None = None, run: Callable = subprocess.run):
        self.root = Path(root)
        self.pgdata = self.root / "pg"
        self._bin = bin_dir
        self._run = run

    def _exe(self, name: str) -> str:
        return str((self._bin or pg_bin_dir()) / name)

    def password(self) -> str:
        path = self.root / "pg.pass"
        if path.is_file() and (pw := path.read_text(encoding="utf-8").strip()):
            return pw
        pw = secrets.token_urlsafe(24)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(pw)
        return pw

    def _init(self) -> None:
        """initdb into a temporary folder and rename it only when complete: an interrupted first start
        (closed app, power cut) never leaves a half-made database that fails on every later start."""
        import shutil

        tmp = self.root / "pg.tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        self.root.mkdir(parents=True, exist_ok=True)
        pwfile = self.root / f"{secrets.token_hex(6)}.pwfile"
        pwfile.write_text(self.password(), encoding="utf-8")
        try:
            self._run([self._exe("initdb"), "-D", str(tmp), "-U", "postgres", "-A", "scram-sha-256", f"--pwfile={pwfile}",
                       "-E", "UTF8", "--locale=C"], check=True, creationflags=NO_WINDOW, **QUIET)  # fmt: skip
        except BaseException:
            shutil.rmtree(tmp, ignore_errors=True)
            raise
        finally:
            pwfile.unlink(missing_ok=True)
        tmp.rename(self.pgdata)

    def start(self) -> str:
        if not (self.pgdata / "PG_VERSION").exists():
            import shutil

            shutil.rmtree(self.pgdata, ignore_errors=True)  # a half-made folder from an older version
            self._init()
        port = free_port()
        # no pipes: postgres inherits them and pg_ctl would never return on Windows
        self._run([self._exe("pg_ctl"), "-D", str(self.pgdata), "-l", str(self.pgdata / "server.log"), "-w", "-t", "60",
                   "-o", f"-h 127.0.0.1 -p {port}", "start"], check=True, creationflags=NO_WINDOW, **QUIET)  # fmt: skip
        return f"postgresql+psycopg://postgres:{self.password()}@127.0.0.1:{port}/postgres"

    def stop(self) -> None:
        if (self.pgdata / "postmaster.pid").exists():
            self._run([self._exe("pg_ctl"), "-D", str(self.pgdata), "-w", "-t", "30", "-m", "fast", "stop"],
                      check=False, creationflags=NO_WINDOW, **QUIET)  # fmt: skip

    def pid(self) -> int | None:
        try:
            return int((self.pgdata / "postmaster.pid").read_text().splitlines()[0])
        except (OSError, ValueError, IndexError):
            return None


def engine_command() -> list[str]:
    """How to start a child of this app: the frozen exe itself, or this Python with the child entry."""
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-c", "from mediafactory.desktop_engine import child_main; child_main()"]


def _health(port: int) -> bool:
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/health", headers={"Host": "127.0.0.1"})
        with urllib.request.urlopen(req, timeout=2) as r:  # noqa: S310 - our own loopback API
            return r.status == 200
    except OSError:
        return False


def _kill_tree(pid: int) -> None:
    try:
        import psutil

        proc = psutil.Process(pid)
        for child in proc.children(recursive=True):
            child.kill()
        proc.kill()
    except Exception:  # noqa: BLE001 - already gone, or no permission: nothing more we can do
        pass


def _pid_created(pid: int) -> float | None:
    """When the process started (None if gone): tells our own process from a later one with the same PID."""
    try:
        import psutil

        return psutil.Process(pid).create_time()
    except Exception:  # noqa: BLE001 - gone, no permission, or psutil missing
        return None


class Engine:
    def __init__(
        self, home: Path, exe: list[str] | None = None, *, popen: Callable = subprocess.Popen, run: Callable = subprocess.run,
        db: EngineDB | None = None, healthy: Callable[[int], bool] = _health, sleep: Callable[[float], None] = time.sleep,
        ffmpeg_dir: Path | None = None,
    ):  # fmt: skip
        self.home = Path(home)
        self.dir = engine_dir(home)
        self.exe = exe or engine_command()
        self._popen, self._run, self._healthy, self._sleep = popen, run, healthy, sleep
        self.db = db or EngineDB(self.dir)
        self.ffmpeg_dir = ffmpeg_dir
        self._kill, self._created = _kill_tree, _pid_created
        self._lock = threading.RLock()
        self._stopping = False
        self.state = "stopped"
        self.last_error: str | None = None
        self.port = 0
        self.procs: dict[str, subprocess.Popen] = {}
        self.restarts = dict.fromkeys(CHILDREN, 0)
        self.env: dict[str, str] = {}

    # ---------- files ----------
    @property
    def stop_file(self) -> Path:
        return self.dir / "engine.stop"

    @property
    def pids_file(self) -> Path:
        return self.dir / "engine.pids"

    def _save_pids(self) -> None:
        pids = {name: {"pid": p.pid, "created": self._created(p.pid)} for name, p in self.procs.items()}
        if (db_pid := self.db.pid()) is not None:
            pids["db"] = {"pid": db_pid, "created": self._created(db_pid)}
        self.pids_file.write_text(json.dumps(pids), encoding="utf-8")

    def _log_tail(self, name: str, n: int = 6) -> str:
        try:
            lines = (self.dir / "logs" / f"{name}.log").read_text(encoding="utf-8", errors="replace").splitlines()
            return "\n".join(lines[-n:])
        except OSError:
            return ""

    # ---------- lifecycle ----------
    def cleanup_stale(self) -> None:
        """After a crash: kill the children listed last time and stop that database."""
        try:
            pids = json.loads(self.pids_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pids = {}
        for name in CHILDREN:
            entry = pids.get(name)
            if not isinstance(entry, dict) or not isinstance(entry.get("pid"), int) or entry.get("created") is None:
                continue  # unknown start time: never kill what might be someone else's program
            now = self._created(entry["pid"])
            if now is not None and abs(now - float(entry["created"])) < 1.0:
                self._kill(entry["pid"])
        if pids or self.db.pid() is not None:
            self.db.stop()
        self.pids_file.unlink(missing_ok=True)
        self.stop_file.unlink(missing_ok=True)

    def _spawn(self, name: str) -> subprocess.Popen | None:
        with self._lock:
            if self._stopping:
                return None  # the app is closing: start nothing new
            return self._spawn_locked(name)

    def _spawn_locked(self, name: str) -> subprocess.Popen:
        cmd = [*self.exe, "--engine", name] + (["--port", str(self.port)] if name == "api" else [])
        env = {**self.env, "MF_LOG_FILE": str(self.dir / "logs" / f"{name}.log")}
        proc = self._popen(cmd, env=env, creationflags=NO_WINDOW, **QUIET)
        self.procs[name] = proc
        return proc

    def start(self, progress: Callable[[str], None] = lambda step: None) -> int:
        self._stopping = False
        self.state, self.last_error = "starting", None
        (self.dir / "logs").mkdir(parents=True, exist_ok=True)
        self.cleanup_stale()
        try:
            progress("database")
            url = self.db.start()
            env = {**os.environ, "MF_DATABASE_URL": url, "MF_SECRET_KEY": secret_key(self.dir), "MF_DATA_DIR": str(self.dir),
                   "MF_LOCAL_MODE": "1", "MF_ALLOWED_HOSTS": '["127.0.0.1","localhost"]', "PYTHONIOENCODING": "utf-8"}  # fmt: skip
            if self.ffmpeg_dir:
                env["PATH"] = str(self.ffmpeg_dir) + os.pathsep + env.get("PATH", "")
            self.env = env
            progress("migrate")
            r = self._run([*self.exe, "--engine", "migrate"], env=env, capture_output=True, text=True,
                          creationflags=NO_WINDOW, stdin=subprocess.DEVNULL)  # fmt: skip
            if r.returncode != 0:
                raise EngineError(f"database setup failed: {(r.stderr or r.stdout or '').strip()[-400:]}")
            progress("services")
            self.port = free_port()
            for name in CHILDREN:
                if self._spawn(name) is None:
                    raise EngineError("the app is closing")
            self._save_pids()
            waited = 0.0
            while not self._healthy(self.port):
                if any(p.poll() is not None for p in self.procs.values()):
                    raise EngineError("the engine stopped while starting:\n" + (self._log_tail("api") or self._log_tail("worker")))
                if waited >= HEALTH_TIMEOUT_S:
                    raise EngineError("the engine did not answer within 90 seconds")
                self._sleep(0.5)
                waited += 0.5
        except Exception as exc:
            self.last_error = str(exc)
            self.stop(timeout_s=5)
            self.state = "failed"
            raise exc if isinstance(exc, EngineError) else EngineError(str(exc)) from exc
        self.state = "running"
        progress("ready")
        return self.port

    def watch_once(self) -> None:
        """Restart a child that died, once; a second death marks the engine failed."""
        if self.state != "running" or self._stopping:
            return
        for name, proc in list(self.procs.items()):
            if proc.poll() is None:
                continue
            if self.restarts[name] >= 1:
                self.state = "failed"
                self.last_error = f"the {name} process stopped twice:\n{self._log_tail(name)}"
                return
            self.restarts[name] += 1
            self._spawn(name)
            self._save_pids()

    def stop(self, timeout_s: float = 20) -> None:
        with self._lock:
            self._stopping = True  # from here on nothing is (re)started
        self.dir.mkdir(parents=True, exist_ok=True)
        self.stop_file.write_text("stop", encoding="utf-8")
        worker = self.procs.get("worker")
        if worker is not None and worker.poll() is None:
            try:
                worker.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                self._kill(worker.pid)
        api = self.procs.get("api")
        if api is not None and api.poll() is None:
            api.terminate()
            try:
                api.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._kill(api.pid)
        self.db.stop()
        self.procs.clear()
        self.stop_file.unlink(missing_ok=True)
        self.pids_file.unlink(missing_ok=True)
        self.state = "stopped"


# ---------- child processes ----------


def _run_cli(args: list[str]) -> None:
    from mediafactory.cli import app

    app(args, prog_name="mf")


def child_main(argv: list[str] | None = None) -> None:
    """Entry for `<app> --engine api|worker|migrate [--port N]`."""
    argv = list(sys.argv[1:] if argv is None else argv)
    kind = argv[argv.index("--engine") + 1]
    if kind == "api":
        port = argv[argv.index("--port") + 1]
        _run_cli(["api", "--host", "127.0.0.1", "--port", port])
    elif kind == "worker":
        _run_cli(["worker"])
    elif kind == "migrate":
        _run_cli(["migrate"])
    else:
        raise SystemExit(f"unknown engine part: {kind}")
