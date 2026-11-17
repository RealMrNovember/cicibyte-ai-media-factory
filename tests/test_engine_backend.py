from mediafactory import cli


def test_worker_stops_when_stop_file_appears(tmp_path):
    assert cli.stop_requested(tmp_path) is False
    (tmp_path / "engine.stop").write_text("")
    assert cli.stop_requested(tmp_path) is True


def test_local_mode_setting_reads_env(monkeypatch):
    from mediafactory.core.config import get_settings

    monkeypatch.setenv("MF_LOCAL_MODE", "1")
    get_settings.cache_clear()
    try:
        assert get_settings().local_mode is True
    finally:
        get_settings.cache_clear()
    monkeypatch.delenv("MF_LOCAL_MODE")
    assert get_settings().local_mode is False
    get_settings.cache_clear()
