import json
from types import SimpleNamespace

from mediafactory.pipeline import story

H = {"X-MF-Client": "1"}
TEXT = " ".join(["Gece yarısı köy evinin tavanından ayak sesleri geliyordu."] * 20)


def test_ai_story_is_added_as_turkish_user_owned_item(client, monkeypatch):
    seen = {}

    def fake_run_task(session, task, messages, **kw):
        seen["task"], seen["system"] = task, messages[0]["content"]
        return SimpleNamespace(text=json.dumps({"title": "Tavandaki Sesler", "story": TEXT}), model="m1", provider_id=1)

    monkeypatch.setattr(story, "run_task", fake_run_task)
    r = client.post("/api/items/ai-story", json={"topic": "köy evi", "language": "tr"}, headers=H)
    assert r.status_code == 201, r.text
    item = r.json()["item"]
    assert item["title"] == "Tavandaki Sesler" and item["language"] == "tr" and item["rights_status"] == "user_owned"
    assert seen["task"] == "script" and "Turkish" in seen["system"]


def test_ai_story_reports_unusable_output(client, monkeypatch):
    monkeypatch.setattr(story, "run_task", lambda *a, **k: SimpleNamespace(text='{"title":"x","story":"too short"}', model="m"))
    assert client.post("/api/items/ai-story", json={"topic": "x"}, headers=H).status_code == 502


def test_story_under_another_key_is_still_used(monkeypatch):
    from mediafactory.pipeline.story import write_story

    reply = json.dumps({"title": "Sis", "content": TEXT})
    monkeypatch.setattr(story, "run_task", lambda *a, **k: SimpleNamespace(text=reply, model="m"))
    assert write_story(None, "sis", language="tr")["story"] == TEXT


def test_plain_text_reply_without_json_is_used_as_the_story(monkeypatch):
    from mediafactory.pipeline.story import write_story

    monkeypatch.setattr(story, "run_task", lambda *a, **k: SimpleNamespace(text="Başlık: Sis\n\n" + TEXT, model="m"))
    out = write_story(None, "sis", language="tr")
    assert TEXT in out["story"] and out["title"] == "sis"
