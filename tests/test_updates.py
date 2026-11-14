import json
import shutil
import subprocess

import pytest

H = {"X-MF-Client": "1"}


@pytest.fixture
def update_dir(tmp_path, monkeypatch):
    from mediafactory.api.routes import system

    d = tmp_path / "update"
    monkeypatch.setattr(system, "_dir", lambda: d)
    return d


def test_system_info_without_updater(client, update_dir):
    data = client.get("/api/system").json()
    assert data["version"] and data["update"] is None and data["auto"] is True


def test_status_and_auto_setting(client, update_dir):
    update_dir.mkdir()
    (update_dir / "update-status.json").write_text(json.dumps({"state": "up_to_date", "current": "abc1234"}))
    assert client.get("/api/system").json()["update"]["current"] == "abc1234"
    assert client.put("/api/system/update-config", json={"auto": False}, headers=H).status_code == 200
    assert json.loads((update_dir / "update-config.json").read_text()) == {"auto": False}
    assert client.get("/api/system").json()["auto"] is False


def test_update_now_writes_request(client, update_dir):
    assert client.post("/api/system/update", json={"force": True}, headers=H).status_code == 202
    assert (update_dir / "update-request").read_text() == "force"
    assert client.post("/api/system/update", json={}, headers=H).status_code == 202
    assert (update_dir / "update-request").read_text() == "now"


def test_busy_reports_running_stages(db, monkeypatch):
    from typer.testing import CliRunner

    from mediafactory import cli
    from mediafactory.db.models import JobStageRun, ProductionJob

    monkeypatch.setattr(cli, "_session_factory", lambda: (lambda: _Nested(db)))
    runner = CliRunner()
    assert runner.invoke(cli.app, ["busy"]).exit_code == 0
    job = ProductionJob(status="rendering", payload={})
    db.add(job)
    db.flush()
    db.add(JobStageRun(job_id=job.id, stage="make_short", job_class="render", state="running"))
    db.flush()
    r = runner.invoke(cli.app, ["busy"])
    assert r.exit_code == 3 and "1" in r.output


class _Nested:
    def __init__(self, s):
        self.s = s

    def __enter__(self):
        return self.s

    def __exit__(self, *a):
        return False


@pytest.mark.skipif(not shutil.which("bash"), reason="bash not available")
def test_update_scripts_parse():
    for script in ("deploy/update/mf-update.sh", "deploy/update/install-autoupdate.sh"):
        assert subprocess.run(["bash", "-n", script]).returncode == 0
