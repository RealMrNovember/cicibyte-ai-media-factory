import json

import httpx
import respx

from mediafactory.ai import client
from mediafactory.db.models import AIProvider

URL = "https://api.example.ai/v1"
OK = {"choices": [{"message": {"content": '{"a": 1}'}}], "model": "m"}


def _p(db, **options):
    p = AIProvider(name="svc", kind="openai_compatible", base_url=URL, locality="remote", timeout_s=30, options=options)
    db.add(p)
    db.flush()
    return p


@respx.mock
def test_prompt_json_mode_sends_no_response_format(db):
    route = respx.post(f"{URL}/chat/completions").mock(return_value=httpx.Response(200, json=OK))
    p = _p(db, json_mode="prompt")
    client.chat(p, "m", [{"role": "user", "content": "hi"}], json_schema={"type": "object"})
    body = json.loads(route.calls[0].request.content)
    assert "response_format" not in body and body["messages"][0]["content"].startswith(client.JSON_INSTRUCTION)
    assert route.call_count == 1


@respx.mock
def test_default_mode_still_tries_json_schema_first(db):
    route = respx.post(f"{URL}/chat/completions").mock(return_value=httpx.Response(200, json=OK))
    client.chat(_p(db), "m", [{"role": "user", "content": "hi"}], json_schema={"type": "object"})
    assert json.loads(route.calls[0].request.content)["response_format"]["type"] == "json_schema"


@respx.mock
def test_extra_headers_are_sent_but_never_replace_the_key(db):
    from mediafactory.core.crypto import encrypt

    route = respx.post(f"{URL}/chat/completions").mock(return_value=httpx.Response(200, json=OK))
    p = _p(db, headers={"anthropic-version": "2023-06-01", "Authorization": "Bearer evil"})
    p.api_key_enc = encrypt("sk-real")
    client.chat(p, "m", [{"role": "user", "content": "hi"}])
    h = route.calls[0].request.headers
    assert h["anthropic-version"] == "2023-06-01" and h["authorization"] == "Bearer sk-real"


@respx.mock
def test_check_key_lists_models_or_sends_a_tiny_chat(db):
    respx.get(f"{URL}/models").mock(return_value=httpx.Response(200, json={"data": [{"id": "a"}, {"id": "b"}]}))
    assert client.check_key(_p(db)) == ["a", "b"]
    route = respx.post(f"{URL}/chat/completions").mock(return_value=httpx.Response(200, json=OK))
    p2 = AIProvider(name="svc2", kind="openai_compatible", base_url=URL, locality="remote", timeout_s=30,
                    options={"check": "chat"})  # fmt: skip
    db.add(p2)
    db.flush()
    assert client.check_key(p2, "claude-x") == ["claude-x"]
    assert json.loads(route.calls[0].request.content)["max_tokens"] == 1


def test_options_travel_with_settings_export(db):
    from mediafactory import portability

    _p(db, json_mode="prompt")
    out = portability.export_settings(db, password=None)
    prov = next(p for p in out["data"]["providers"] if p["name"] == "svc")
    assert prov["options"] == {"json_mode": "prompt"}
    db.delete(db.query(AIProvider).filter_by(name="svc").one())
    db.flush()
    portability.import_settings(db, out, password=None)
    assert db.query(AIProvider).filter_by(name="svc").one().options == {"json_mode": "prompt"}


@respx.mock
def test_services_that_reject_sampling_get_no_temperature(db):
    route = respx.post(f"{URL}/chat/completions").mock(return_value=httpx.Response(200, json=OK))
    client.chat(_p(db, no_temperature=True), "m", [{"role": "user", "content": "hi"}], temperature=0.7)
    assert "temperature" not in json.loads(route.calls[0].request.content)


@respx.mock
def test_json_is_also_asked_for_in_the_prompt_when_the_format_is_sent(db):
    """A service may accept response_format and still ignore it: the prompt asks for JSON too."""
    route = respx.post(f"{URL}/chat/completions").mock(return_value=httpx.Response(200, json=OK))
    client.chat(_p(db), "m", [{"role": "user", "content": "hi"}], json_schema={"type": "object"})
    body = json.loads(route.calls[0].request.content)
    assert body["response_format"]["type"] == "json_schema"
    assert body["messages"][0]["content"].startswith(client.JSON_INSTRUCTION)
