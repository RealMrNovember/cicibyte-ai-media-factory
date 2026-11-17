import threading

from mediafactory.pipeline import assets

H = {"X-MF-Client": "1"}


def test_downloads_report_progress_and_finish(tmp_path):
    seen = []
    d = assets.Downloader(tmp_path, steps=[("voice-en", lambda m: seen.append("en")), ("voice-tr", lambda m: seen.append("tr")),
                                           ("captions", lambda m: seen.append("w"))])  # fmt: skip
    d.run()
    st = d.status()
    assert seen == ["en", "tr", "w"] and st["state"] == "done" and st["done"] == st["total"] == 3


def test_a_failed_download_is_reported_and_can_be_retried(tmp_path):
    calls = {"n": 0}

    def flaky(m):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("no internet")

    d = assets.Downloader(tmp_path, steps=[("voice-en", flaky)])
    d.run()
    assert d.status()["state"] == "failed" and "no internet" in d.status()["error"]
    d.run()
    assert d.status()["state"] == "done"


def test_start_does_not_run_twice_at_once(tmp_path):
    gate = threading.Event()
    runs = []

    def slow(m):
        runs.append(1)
        gate.wait(5)

    d = assets.Downloader(tmp_path, steps=[("voice-en", slow)])
    assert d.start() is True
    assert d.start() is False
    gate.set()
    d.thread.join(5)
    assert runs == [1]


def test_api_starts_and_reports(client, monkeypatch, tmp_path):
    fake = assets.Downloader(tmp_path, steps=[("voice-en", lambda m: None)])
    monkeypatch.setattr(assets, "shared", lambda data_dir: fake)
    r = client.post("/api/ai-setup/assets", headers=H)
    assert r.status_code == 200
    fake.thread.join(5)
    assert client.get("/api/ai-setup/assets", headers=H).json()["state"] == "done"
