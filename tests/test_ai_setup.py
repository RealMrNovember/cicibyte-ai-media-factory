import json

import httpx
import pytest
import respx
from sqlalchemy import select

from mediafactory.ai import discovery, presets
from mediafactory.db.models import AIProvider, AITaskRoute, SystemSetting

H = {"X-MF-Client": "1"}


@pytest.fixture
def local_mode(monkeypatch):
    from mediafactory.core.config import get_settings

    monkeypatch.setenv("MF_LOCAL_MODE", "1")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_presets_have_what_the_wizard_needs():
    ids = [p["id"] for p in presets.PRESETS]
    assert {"openai", "anthropic", "gemini", "openrouter", "groq", "deepseek", "mistral", "xai"} <= set(ids)
    for p in presets.PRESETS:
        assert p["base_url"].startswith("https://") and p["key_url"].startswith("https://") and p["models"]
    claude = presets.get("anthropic")
    assert claude["base_url"] == "https://api.anthropic.com/v1"
    assert claude["options"]["check"] == "chat" and claude["options"]["no_temperature"] is True


@respx.mock
def test_scan_finds_ollama_and_lm_studio_on_this_computer():
    respx.get("http://127.0.0.1:11434/api/version").mock(return_value=httpx.Response(200, json={"version": "0.9"}))
    respx.get("http://127.0.0.1:11434/v1/models").mock(return_value=httpx.Response(200, json={"data": [{"id": "llama3.1:8b"}]}))
    respx.get("http://127.0.0.1:1234/v1/models").mock(return_value=httpx.Response(200, json={"data": [{"id": "qwen2.5-7b-instruct"}]}))
    respx.route(host="127.0.0.1").mock(side_effect=httpx.ConnectError("refused"))
    found = {f["tool"]: f for f in discovery.scan()}
    assert found["ollama"]["base_url"] == "http://127.0.0.1:11434/v1" and found["ollama"]["models"] == ["llama3.1:8b"]
    assert found["lmstudio"]["models"] == ["qwen2.5-7b-instruct"]
    assert "jan" not in found


def test_rank_puts_bigger_instruct_models_first():
    assert discovery.rank(["tiny-embed", "llama3.1:8b", "qwen2.5:32b-instruct", "phi3:3.8b"])[0] == "qwen2.5:32b-instruct"


def test_setup_status_lists_presets_and_says_nothing_is_configured(client):
    st = client.get("/api/ai-setup", headers=H).json()
    assert st["configured"] is False and st["local_mode"] is False and len(st["presets"]) >= 8


def test_custom_address_is_refused_outside_local_mode(client):
    r = client.post("/api/ai-setup/check", json={"base_url": "http://10.0.0.5:11434/v1"}, headers=H)
    assert r.status_code == 403


def test_custom_address_is_checked_in_local_mode(client, local_mode, monkeypatch):
    from mediafactory.ai import client as ai_client

    monkeypatch.setattr(ai_client, "check_key", lambda p, model=None: ["m1", "m2"])
    r = client.post("/api/ai-setup/check", json={"base_url": "http://192.168.1.20:11434"}, headers=H)
    assert r.status_code == 200 and r.json() == {"ok": True, "models": ["m1", "m2"], "base_url": "http://192.168.1.20:11434/v1"}


def test_preset_check_reports_a_bad_key_in_plain_words(client, monkeypatch):
    from mediafactory.ai import client as ai_client

    def refuse(p, model=None):
        raise ai_client.ProviderError("HTTP 401: invalid x-api-key", retryable=False, status=401)

    monkeypatch.setattr(ai_client, "check_key", refuse)
    r = client.post("/api/ai-setup/check", json={"preset": "anthropic", "api_key": "sk-bad", "model": "claude-sonnet-5-5"}, headers=H)
    body = r.json()
    assert r.status_code == 200 and body["ok"] is False and body["reason"] == "bad_key"
    assert "sk-bad" not in json.dumps(body)


def _apply(client, **extra):
    body = {"preset": "openai", "api_key": "sk-test-123456", "script_model": "gpt-x", "classify_model": "gpt-y", **extra}
    return client.post("/api/ai-setup/apply", json=body, headers=H)


def test_apply_creates_the_provider_and_routes(client, db):
    r = _apply(client)
    assert r.status_code == 200, r.text
    prov = db.scalar(select(AIProvider).where(AIProvider.name == "OpenAI"))
    assert prov.api_key_enc and "sk-test" not in prov.api_key_enc
    routes = {x.task: x.steps for x in db.scalars(select(AITaskRoute))}
    assert routes["script"] == [{"provider_id": prov.id, "model": "gpt-x"}]
    assert routes["classify"] == [{"provider_id": prov.id, "model": "gpt-y"}]
    assert "sk-test" not in r.text


def test_apply_as_primary_keeps_existing_steps_as_backup(client, db):
    old = AIProvider(name="router", kind="openai_compatible", base_url="http://r/v1", locality="remote", timeout_s=60)
    db.add(old)
    db.flush()
    db.add(AITaskRoute(task="script", steps=[{"provider_id": old.id, "model": "old-m"}], rounds=3, retry_delay_s=3))
    db.flush()
    _apply(client)
    steps = db.scalar(select(AITaskRoute).where(AITaskRoute.task == "script")).steps
    assert [s["model"] for s in steps] == ["gpt-x", "old-m"]
    _apply(client, mode="only")
    steps = db.scalar(select(AITaskRoute).where(AITaskRoute.task == "script")).steps
    assert [s["model"] for s in steps] == ["gpt-x"]


def test_try_runs_a_short_script_in_both_languages(client, monkeypatch):
    from mediafactory.ai import router

    _apply(client)

    class R:
        text = "Bir gece kapı çaldı."

    monkeypatch.setattr(router, "run_task", lambda db, task, messages, **kw: R())
    body = client.post("/api/ai-setup/try", headers=H).json()
    assert body["ok"] is True and body["sample"]["tr"].startswith("Bir gece") and "seconds" in body


def test_done_marks_setup_complete(client, db):
    client.post("/api/ai-setup/done", headers=H)
    assert db.get(SystemSetting, "setup").value["done"] is True
    assert client.get("/api/ai-setup", headers=H).json()["setup_done"] is True


def test_a_service_checked_by_chat_still_offers_all_its_models(client, monkeypatch):
    from mediafactory.ai import client as ai_client

    monkeypatch.setattr(ai_client, "check_key", lambda p, model=None: [model])
    body = client.post("/api/ai-setup/check", json={"preset": "anthropic", "api_key": "k", "model": "claude-opus-5-5"}, headers=H).json()
    assert body["ok"] and body["models"] == presets.get("anthropic")["models"]


def test_own_ai_servers_get_the_long_local_timeout(client, db, local_mode):
    client.post("/api/ai-setup/apply", json={"base_url": "http://192.168.1.20:11434", "script_model": "m", "classify_model": "m"},
                headers=H)  # fmt: skip
    prov = db.scalar(select(AIProvider).where(AIProvider.name == "AI server"))
    assert prov.locality == "local" and prov.timeout_s == 600
