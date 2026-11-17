import json

import pytest

from mediafactory import desktop_engine as de


class FakeProc:
    def __init__(self, cmd, exits_after_stop=True):
        self.cmd, self.returncode, self.killed, self.terminated = cmd, None, False, False
        self.pid = 1000 + len(cmd)
        self.exits_after_stop = exits_after_stop

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        if self.returncode is None:
            raise de.subprocess.TimeoutExpired(self.cmd, timeout)
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    def kill(self):
        self.killed = True
        self.returncode = -9


class FakeDB:
    def __init__(self):
        self.started = self.stopped = 0

    def start(self):
        self.started += 1
        return "postgresql+psycopg://postgres@127.0.0.1:5999/postgres"

    def stop(self):
        self.stopped += 1

    def pid(self):
        return 4242 if self.started > self.stopped else None


def _engine(tmp_path, procs, **kw):
    def popen(cmd, **k):
        p = FakeProc(cmd)
        p.env = k.get("env")
        procs.append(p)
        return p

    runs = []

    def run(cmd, **k):
        runs.append(cmd)
        return de.subprocess.CompletedProcess(cmd, 0, "", "")

    e = de.Engine(tmp_path, ["mfexe"], popen=popen, run=run, db=FakeDB(), healthy=lambda port: True, sleep=lambda s: None, **kw)
    e.runs = runs
    return e


def test_secret_key_is_created_once_and_reused(tmp_path):
    k1 = de.secret_key(tmp_path)
    assert len(k1) >= 48 and de.secret_key(tmp_path) == k1


def test_second_instance_cannot_take_the_lock(tmp_path):
    a, b = de.SingleInstance(tmp_path), de.SingleInstance(tmp_path)
    assert a.acquire() is True
    assert b.acquire() is False
    a.release()
    assert b.acquire() is True
    b.release()


def test_start_migrates_then_runs_api_and_worker_with_engine_env(tmp_path):
    procs = []
    e = _engine(tmp_path, procs)
    port = e.start()
    assert e.state == "running" and port > 0
    assert e.runs[0] == ["mfexe", "--engine", "migrate"]
    kinds = [p.cmd[2] for p in procs]
    assert kinds == ["api", "worker"] and procs[0].cmd[-1] == str(port)
    env = procs[1].env
    assert env["MF_LOCAL_MODE"] == "1" and env["MF_DATA_DIR"] == str(de.engine_dir(tmp_path))
    assert env["MF_DATABASE_URL"].endswith("127.0.0.1:5999/postgres") and len(env["MF_SECRET_KEY"]) >= 48
    assert json.loads((de.engine_dir(tmp_path) / "engine.pids").read_text())["worker"] == procs[1].pid


def test_stop_asks_the_worker_with_a_file_then_kills_after_the_timeout(tmp_path):
    procs = []
    e = _engine(tmp_path, procs)
    e.start()
    seen = {}

    def kill_tree(pid):
        seen.setdefault("killed", []).append(pid)
        for p in procs:
            if p.pid == pid:
                p.kill()

    e._kill = kill_tree
    e.stop(timeout_s=0)
    worker = procs[1]
    assert worker.killed and e.db.stopped == 1 and e.state == "stopped"
    assert not (de.engine_dir(tmp_path) / "engine.stop").exists()
    assert not (de.engine_dir(tmp_path) / "engine.pids").exists()


def test_stop_file_is_written_before_waiting(tmp_path):
    procs = []
    e = _engine(tmp_path, procs)
    e.start()
    stop_file = de.engine_dir(tmp_path) / "engine.stop"

    def wait(timeout=None):
        assert stop_file.exists()  # the worker is asked first
        procs[1].returncode = 0
        return 0

    procs[1].wait = wait
    e.stop(timeout_s=5)
    assert not procs[1].killed and procs[0].terminated


def test_stale_processes_from_a_crash_are_cleaned_up(tmp_path):
    d = de.engine_dir(tmp_path)
    d.mkdir(parents=True)
    (d / "engine.pids").write_text(json.dumps({"api": 11, "worker": 12, "db": 13}))
    procs = []
    e = _engine(tmp_path, procs)
    killed = []
    e._kill = killed.append
    e._alive = lambda pid: True
    e.cleanup_stale()
    assert sorted(killed) == [11, 12] and e.db.stopped == 1
    assert not (d / "engine.pids").exists()


def test_a_dead_child_is_restarted_once_then_the_engine_reports_failure(tmp_path):
    procs = []
    e = _engine(tmp_path, procs)
    e.start()
    procs[1].returncode = 1
    e.watch_once()
    assert e.state == "running" and len(procs) == 3 and procs[2].cmd[2] == "worker"
    procs[2].returncode = 1
    (de.engine_dir(tmp_path) / "logs").mkdir(exist_ok=True)
    (de.engine_dir(tmp_path) / "logs" / "worker.log").write_text("boom: font missing\n")
    e.watch_once()
    assert e.state == "failed" and "font missing" in e.last_error


def test_failed_migration_reports_an_error_and_stops_the_database(tmp_path):
    procs = []
    e = _engine(tmp_path, procs)
    e._run = lambda cmd, **k: de.subprocess.CompletedProcess(cmd, 1, "", "relation broken")
    with pytest.raises(de.EngineError, match="relation broken"):
        e.start()
    assert e.state == "failed" and e.db.stopped == 1 and procs == []


def test_child_main_maps_engine_kinds_to_cli_commands(monkeypatch):
    seen = []
    monkeypatch.setattr(de, "_run_cli", lambda args: seen.append(args))
    de.child_main(["--engine", "api", "--port", "5123"])
    de.child_main(["--engine", "worker"])
    de.child_main(["--engine", "migrate"])
    assert seen == [["api", "--host", "127.0.0.1", "--port", "5123"], ["worker"], ["migrate"]]
