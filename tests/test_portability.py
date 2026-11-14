import json

import pytest
from sqlalchemy import select

from mediafactory.core.crypto import decrypt, encrypt
from mediafactory.db.models import AIProvider, AITaskRoute, Schedule, SourceConnector, YouTubeChannel
from mediafactory.portability import PortabilityError, export_settings, import_settings
from mediafactory.sources.credentials import get_reddit_credentials, set_reddit_credentials
from mediafactory.youtube import oauth

H = {"X-MF-Client": "1"}


def _seed(db):
    p = AIProvider(name="router", base_url="http://ai-router:20128/v1", api_key_enc=encrypt("sk-router-123"), timeout_s=300)
    db.add(p)
    db.flush()
    db.add(AITaskRoute(task="script", steps=[{"provider_id": p.id, "model": "mf-senaryo"}], rounds=3, retry_delay_s=3.0))
    db.add(SourceConnector(name="BBC Türkçe", adapter="rss", params={"url": "https://feeds.bbci.co.uk/turkce/rss.xml"},
                           enabled=False, poll_interval_min=120, default_language="tr"))  # fmt: skip
    db.add(Schedule(name="Daily", kind="produce", enabled=True, times=["09:00"], weekdays=[0, 1], timezone="Europe/Istanbul",
                    params={"count": 2}))  # fmt: skip
    oauth.set_client(db, "cid-1234567890.apps.googleusercontent.com", "yt-secret")
    db.add(YouTubeChannel(channel_id="UC1", title="Night Tales", refresh_token_enc=encrypt("refresh-1"), is_default=True))
    set_reddit_credentials(db, "reddit-id", "reddit-secret")
    db.flush()


def _wipe(db):
    for model in (AITaskRoute, AIProvider, SourceConnector, Schedule, YouTubeChannel):
        for row in db.scalars(select(model)):
            db.delete(row)
    from mediafactory.db.models import SystemSetting

    for row in db.scalars(select(SystemSetting)):
        db.delete(row)
    db.flush()


def test_export_without_password_has_no_secrets(db):
    _seed(db)
    data = export_settings(db, password=None)
    blob = json.dumps(data)
    assert "sk-router-123" not in blob and "yt-secret" not in blob and "refresh-1" not in blob
    assert data["secrets"] is None and data["data"]["providers"][0]["name"] == "router"
    assert data["data"]["routes"][0]["steps"] == [{"provider": "router", "model": "mf-senaryo"}]  # by name, not id


def test_round_trip_with_password_restores_everything(db):
    _seed(db)
    data = json.loads(json.dumps(export_settings(db, password="correct horse")))
    assert "sk-router-123" not in json.dumps(data)  # secrets are encrypted
    _wipe(db)
    summary = import_settings(db, data, password="correct horse")
    assert summary["providers"] == 1 and summary["sources"] == 1 and summary["schedules"] == 1
    p = db.scalar(select(AIProvider).where(AIProvider.name == "router"))
    assert decrypt(p.api_key_enc) == "sk-router-123" and p.timeout_s == 300
    route = db.scalar(select(AITaskRoute).where(AITaskRoute.task == "script"))
    assert route.steps == [{"provider_id": p.id, "model": "mf-senaryo"}]
    src = db.scalar(select(SourceConnector).where(SourceConnector.name == "BBC Türkçe"))
    assert src.enabled is False and src.default_language == "tr"
    sch = db.scalar(select(Schedule).where(Schedule.name == "Daily"))
    assert sch.times == ["09:00"] and sch.next_run_at is not None
    assert oauth.get_client(db)["client_secret"] == "yt-secret"
    assert decrypt(db.scalar(select(YouTubeChannel)).refresh_token_enc) == "refresh-1"
    assert get_reddit_credentials(db)["client_secret"] == "reddit-secret"


def test_wrong_password_is_refused(db):
    _seed(db)
    data = export_settings(db, password="right")
    with pytest.raises(PortabilityError):
        import_settings(db, data, password="wrong")


def test_import_merges_without_duplicates(db):
    _seed(db)
    data = export_settings(db, password=None)
    summary = import_settings(db, data, password=None)
    assert len(list(db.scalars(select(AIProvider)))) == 1 and len(list(db.scalars(select(SourceConnector)))) == 1
    assert summary["providers"] == 1  # updated in place
    p = db.scalar(select(AIProvider))
    assert decrypt(p.api_key_enc) == "sk-router-123"  # kept: the file had no secrets


def test_rejects_foreign_files(db):
    with pytest.raises(PortabilityError):
        import_settings(db, {"format": "something-else"}, password=None)


def test_api_export_and_import(client, db):
    _seed(db)
    r = client.post("/api/settings/export", json={"password": "pw-123456"}, headers=H)
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    exported = r.content
    _wipe(db)
    r = client.post("/api/settings/import", headers=H, data={"password": "pw-123456"},
                    files={"file": ("mf-settings.json", exported, "application/json")})  # fmt: skip
    assert r.status_code == 200 and r.json()["providers"] == 1
    bad = client.post("/api/settings/import", headers=H, data={"password": "nope"},
                      files={"file": ("mf-settings.json", exported, "application/json")})  # fmt: skip
    assert bad.status_code == 400
