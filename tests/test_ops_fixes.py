import threading

import pytest
from typer.testing import CliRunner

from mediafactory import cli
from mediafactory.core.throttle import MemoryHostThrottle

H = {"X-MF-Client": "1"}


def test_throttle_spaces_requests_from_parallel_threads():
    """Two threads asking at once must not both go immediately: the second waits a full interval."""
    now = [0.0]
    waits = []
    lock = threading.Lock()

    def sleep(s):
        with lock:
            waits.append(round(s, 3))

    t = MemoryHostThrottle(default_interval_s=2.0, sleep=sleep, clock=lambda: now[0])
    threads = [threading.Thread(target=t.acquire, args=("example.com",)) for _ in range(3)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert sorted(waits) == [2.0, 4.0]


def test_missing_settings_give_a_clear_message(monkeypatch):
    monkeypatch.delenv("MF_SECRET_KEY", raising=False)
    monkeypatch.setattr(cli, "_load_settings", cli._load_settings)  # the real loader, settings cache cleared below
    from mediafactory.core.config import get_settings

    get_settings.cache_clear()
    try:
        result = CliRunner().invoke(cli.app, ["migrate"], env={"MF_SECRET_KEY": ""})
    finally:
        get_settings.cache_clear()
    assert result.exit_code == 2
    assert "MF_SECRET_KEY" in result.output and "Traceback" not in result.output


def test_migrate_waits_for_the_database(monkeypatch):
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise OSError("connection refused")

    slept = []
    assert cli.wait_for_database(flaky, timeout_s=30, sleep=slept.append) is True
    assert calls["n"] == 3 and slept == [2, 2]
    calls["n"] = -100
    assert cli.wait_for_database(flaky, timeout_s=4, sleep=lambda s: None) is False


def test_healthcheck_uses_an_allowed_host_name(monkeypatch):
    seen = {}

    class Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout):
        seen["host"], seen["url"] = req.get_header("Host"), req.full_url
        return Resp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setenv("MF_ALLOWED_HOSTS", '["mediafactory","mediafactory.tail1.ts.net"]')
    from mediafactory.core.config import get_settings

    get_settings.cache_clear()
    try:
        result = CliRunner().invoke(cli.app, ["healthcheck"])
    finally:
        get_settings.cache_clear()
    assert result.exit_code == 0 and seen["host"] == "mediafactory" and seen["url"].startswith("http://127.0.0.1:")


@pytest.mark.parametrize("wildcard", ['["*"]', '["*.example.com"]'])
def test_healthcheck_falls_back_to_localhost_for_wildcards(monkeypatch, wildcard):
    from mediafactory.cli import health_host

    monkeypatch.setenv("MF_ALLOWED_HOSTS", wildcard)
    assert health_host(["*"]) == "localhost" and health_host(["*.example.com"]) == "localhost"


def test_reddit_key_that_cannot_be_read_is_reported(client, db):
    from mediafactory.db.models import SystemSetting
    from mediafactory.sources.credentials import REDDIT_KEY

    db.add(SystemSetting(key=REDDIT_KEY, value={"client_id": "abc", "client_secret_enc": "not-a-valid-token"}))
    db.flush()
    st = client.get("/api/source-credentials", headers=H).json()["reddit"]
    assert st["configured"] is False and st["unreadable"] is True and st["client_id"] == "abc"
