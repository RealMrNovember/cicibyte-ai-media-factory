import json

import httpx
import pytest
import respx

from mediafactory.ai.client import ProviderError, chat
from mediafactory.core.crypto import encrypt
from mediafactory.db.models import AIProvider

BASE = "http://llm.test/v1"
MSG = [{"role": "user", "content": "hi"}]


def provider(locality="remote", key="sk-test-key"):
    return AIProvider(
        id=7,
        name="p",
        kind="openai_compatible",
        base_url=BASE,
        api_key_enc=encrypt(key) if key else None,
        locality=locality,
        timeout_s=5,
        max_concurrency=1,
        enabled=True,
    )


def ok(text, model="m1"):
    return {"model": model, "choices": [{"message": {"content": text}}], "usage": {"total_tokens": 3}}


@respx.mock
def test_chat_plain_text():
    route = respx.post(f"{BASE}/chat/completions").mock(return_value=httpx.Response(200, json=ok("hello")))
    r = chat(provider(), "m1", MSG)
    assert r.text == "hello" and r.model == "m1" and r.provider_id == 7
    assert route.calls[0].request.headers["Authorization"] == "Bearer sk-test-key"


@respx.mock
def test_chat_streaming_local_concatenates_chunks():
    chunks = [{"model": "m1", "choices": [{"delta": {"content": c}}]} for c in ("Hel", "lo")]
    body = "".join(f"data: {json.dumps(c)}\n\n" for c in chunks) + "data: [DONE]\n\n"
    route = respx.post(f"{BASE}/chat/completions").mock(
        return_value=httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})
    )
    r = chat(provider(locality="local"), "m1", MSG)
    assert r.text == "Hello"
    assert json.loads(route.calls[0].request.content)["stream"] is True


@respx.mock
def test_json_schema_falls_back_to_json_object_on_400():
    calls = []

    def handler(request):
        fmt = json.loads(request.content).get("response_format", {}).get("type")
        calls.append(fmt)
        if fmt == "json_schema":
            return httpx.Response(400, json={"error": "response_format json_schema unsupported"})
        return httpx.Response(200, json=ok('{"a": 1}'))

    respx.post(f"{BASE}/chat/completions").mock(side_effect=handler)
    r = chat(provider(), "m1", MSG, json_schema={"type": "object"})
    assert calls == ["json_schema", "json_object"]
    assert json.loads(r.text) == {"a": 1}


@respx.mock
def test_prompt_mode_when_no_format_supported():
    seen = []

    def handler(request):
        payload = json.loads(request.content)
        seen.append(payload.get("response_format", {}).get("type"))
        if "response_format" in payload:
            return httpx.Response(422, json={"error": "bad"})
        assert "JSON" in payload["messages"][0]["content"]
        return httpx.Response(200, json=ok('{"a": 2}'))

    respx.post(f"{BASE}/chat/completions").mock(side_effect=handler)
    r = chat(provider(), "m1", MSG, json_schema={"type": "object"})
    assert seen == ["json_schema", "json_object", None]
    assert json.loads(r.text) == {"a": 2}


@respx.mock
def test_html_error_page_raises_provider_error():
    respx.post(f"{BASE}/chat/completions").mock(
        return_value=httpx.Response(
            200, text="<html><body>Bad gateway</body></html>", headers={"content-type": "text/html"}
        )
    )
    with pytest.raises(ProviderError):
        chat(provider(), "m1", MSG)


@respx.mock
def test_5xx_is_retryable_and_4xx_is_not():
    respx.post(f"{BASE}/chat/completions").mock(return_value=httpx.Response(503, text="busy"))
    with pytest.raises(ProviderError) as e:
        chat(provider(), "m1", MSG)
    assert e.value.retryable and e.value.status == 503
    respx.post(f"{BASE}/chat/completions").mock(return_value=httpx.Response(401, text="nope"))
    with pytest.raises(ProviderError) as e:
        chat(provider(), "m1", MSG)
    assert not e.value.retryable


@respx.mock
def test_timeout_is_retryable():
    respx.post(f"{BASE}/chat/completions").mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(ProviderError) as e:
        chat(provider(), "m1", MSG)
    assert e.value.retryable


@respx.mock
def test_empty_content_raises():
    respx.post(f"{BASE}/chat/completions").mock(return_value=httpx.Response(200, json=ok("")))
    with pytest.raises(ProviderError):
        chat(provider(), "m1", MSG)


@respx.mock
def test_no_api_key_sends_no_auth_header():
    route = respx.post(f"{BASE}/chat/completions").mock(return_value=httpx.Response(200, json=ok("x")))
    chat(provider(key=None), "m1", MSG)
    assert "Authorization" not in route.calls[0].request.headers
