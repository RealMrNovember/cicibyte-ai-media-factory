# Adapted from purffle-shorts (MIT, Copyright (c) 2025 Purffle), commit 514fd2547227b98d951dfc1489fc8c7ce72f1b68
"""OpenAI-compatible chat client (Ollama /v1, llama.cpp, 9router, LM Studio, OpenRouter, OpenAI, ...)."""

import json
from dataclasses import dataclass, field

import httpx

from mediafactory.core.crypto import SecretDecryptError, decrypt
from mediafactory.core.redact import redact
from mediafactory.db.models import AIProvider

JSON_INSTRUCTION = "Respond with only a single valid JSON value that matches this JSON Schema, no prose:\n"


@dataclass
class ChatResult:
    text: str
    model: str
    provider_id: int
    usage: dict = field(default_factory=dict)


class ProviderError(Exception):
    def __init__(self, message: str, *, retryable: bool, status: int | None = None):
        super().__init__(redact(message))
        self.retryable = retryable
        self.status = status


def _options(provider: AIProvider) -> dict:
    return provider.options if isinstance(getattr(provider, "options", None), dict) else {}


def _headers(provider: AIProvider) -> dict[str, str]:
    extra = {str(k): str(v) for k, v in (_options(provider).get("headers") or {}).items()
             if str(k).lower() not in ("authorization", "content-type", "host")}  # fmt: skip
    headers = {"Content-Type": "application/json", **extra}
    if provider.api_key_enc:
        try:
            headers["Authorization"] = f"Bearer {decrypt(provider.api_key_enc)}"
        except SecretDecryptError:
            raise ProviderError(
                f"API key of provider '{provider.name}' cannot be decrypted; re-enter it", retryable=False
            ) from None
    return headers


def _format_attempts(json_schema: dict | None, json_mode: str = "auto") -> list[str | None]:
    """Response formats to try in order. "prompt": the service ignores response_format (e.g. Anthropic's
    OpenAI-compatible endpoint), so ask for JSON in the prompt right away."""
    if json_schema is None or json_mode == "prompt":
        return [None]
    return ["json_schema", "json_object", None]


def _payload(model, messages, json_schema, fmt, max_tokens, temperature, stream) -> dict:
    msgs = list(messages)
    if json_schema is not None and fmt is None:
        msgs = [{"role": "system", "content": JSON_INSTRUCTION + json.dumps(json_schema)}, *msgs]
    payload: dict = {"model": model, "messages": msgs, "stream": stream}
    if fmt == "json_schema":
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "reply", "schema": json_schema, "strict": True},
        }
    elif fmt == "json_object":
        payload["response_format"] = {"type": "json_object"}
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if temperature is not None:
        payload["temperature"] = temperature
    return payload


def _looks_like_html(response: httpx.Response, text: str) -> bool:
    return "html" in response.headers.get("content-type", "") or text.lstrip().startswith("<")


def _read_stream(response: httpx.Response) -> tuple[str, str]:
    parts: list[str] = []
    model = ""
    for line in response.iter_lines():
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        try:
            chunk = json.loads(data)
        except json.JSONDecodeError:
            continue
        if not isinstance(chunk, dict):
            continue
        model = chunk.get("model") or model
        for choice in chunk.get("choices") or []:
            delta = choice.get("delta") if isinstance(choice, dict) else None
            content = delta.get("content") if isinstance(delta, dict) else None
            if isinstance(content, str):
                parts.append(content)
    return "".join(parts), model


def _send(client: httpx.Client, url: str, provider: AIProvider, payload: dict, model: str) -> ChatResult:
    with client.stream("POST", url, json=payload, headers=_headers(provider)) as response:
        if response.status_code >= 400:
            body = response.read().decode("utf-8", "replace")[:300]
            retryable = response.status_code == 429 or response.status_code >= 500
            raise ProviderError(f"HTTP {response.status_code}: {body}", retryable=retryable, status=response.status_code)
        if payload["stream"] and "event-stream" in response.headers.get("content-type", ""):
            text, used_model = _read_stream(response)
            usage: dict = {}
        else:
            raw = response.read().decode("utf-8", "replace")
            if _looks_like_html(response, raw):
                raise ProviderError("provider returned an HTML page instead of JSON", retryable=True)
            try:
                data = json.loads(raw)
                text = data["choices"][0]["message"].get("content") or ""
                if not isinstance(text, str):
                    raise TypeError("content is not a string")
            except (json.JSONDecodeError, KeyError, IndexError, TypeError, AttributeError):
                raise ProviderError(f"unparseable provider response: {raw[:200]}", retryable=True) from None
            used_model, usage = data.get("model") or model, data.get("usage") or {}
    if not text.strip():
        raise ProviderError("provider returned empty content", retryable=True)
    return ChatResult(text=text, model=used_model or model, provider_id=provider.id, usage=usage)


def chat(
    provider: AIProvider,
    model: str,
    messages: list[dict],
    *,
    json_schema: dict | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> ChatResult:
    url = provider.base_url.rstrip("/") + "/chat/completions"
    stream = provider.locality == "local"
    attempts = _format_attempts(json_schema, _options(provider).get("json_mode", "auto"))
    if _options(provider).get("no_temperature"):
        temperature = None  # e.g. Anthropic's compatibility layer rejects any value below 1 on current models
    try:
        with httpx.Client(timeout=httpx.Timeout(provider.timeout_s, connect=10)) as client:
            for i, fmt in enumerate(attempts):
                payload = _payload(model, messages, json_schema, fmt, max_tokens, temperature, stream)
                try:
                    return _send(client, url, provider, payload, model)
                except ProviderError as exc:
                    if exc.status in (400, 422) and i < len(attempts) - 1:
                        continue  # format not supported; step down to the next one
                    raise
    except httpx.TimeoutException as exc:
        raise ProviderError(f"timeout after {provider.timeout_s}s: {exc}", retryable=True) from None
    except httpx.HTTPError as exc:  # transport, decoding and protocol errors
        raise ProviderError(f"{type(exc).__name__}: {exc}", retryable=True) from None
    raise ProviderError("no response format accepted", retryable=False)


def check_key(provider: AIProvider, model: str | None = None) -> list[str]:
    """Prove the address and key work: list the models, or (options.check == "chat") send a 1-token chat."""
    if _options(provider).get("check") == "chat":
        if not model:
            raise ProviderError("choose a model to test this service with", retryable=False)
        url = provider.base_url.rstrip("/") + "/chat/completions"
        payload = {"model": model, "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 1, "stream": False}
        try:
            r = httpx.post(url, json=payload, headers=_headers(provider), timeout=30)
        except httpx.HTTPError as exc:
            raise ProviderError(f"connection error: {exc}", retryable=True) from None
        if r.status_code >= 400:
            raise ProviderError(f"HTTP {r.status_code}: {r.text[:200]}", retryable=False, status=r.status_code)
        return [model]
    return list_models(provider)


def list_models(provider: AIProvider) -> list[str]:
    url = provider.base_url.rstrip("/") + "/models"
    try:
        response = httpx.get(url, headers=_headers(provider), timeout=15)
    except httpx.HTTPError as exc:
        raise ProviderError(f"connection error: {exc}", retryable=True) from None
    if response.status_code >= 400:
        raise ProviderError(f"HTTP {response.status_code}: {response.text[:200]}", retryable=False, status=response.status_code)
    try:
        return [m["id"] for m in response.json().get("data", [])]
    except (ValueError, KeyError, TypeError, AttributeError):
        raise ProviderError("unparseable /models response", retryable=False) from None
