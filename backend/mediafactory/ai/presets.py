"""Ready-made AI services for Easy Setup. All speak the OpenAI-compatible chat API, so one client fits.

`models` are suggestions (the first is preselected when the service lists it); the live model list from the
service wins. `options` carry each service's quirks (see AIProvider.options). Update with each release.
"""

PRESETS: list[dict] = [
    {"id": "openai", "name": "OpenAI", "base_url": "https://api.openai.com/v1",
     "key_url": "https://platform.openai.com/api-keys", "models": ["gpt-5-mini", "gpt-5", "gpt-4.1-mini"], "options": {}},
    # Anthropic's OpenAI-compatible layer: Bearer auth works; current models reject temperature < 1, and the
    # key is checked with a 1-token chat (its model list needs Anthropic's own headers).
    {"id": "anthropic", "name": "Anthropic (Claude)", "base_url": "https://api.anthropic.com/v1",
     "key_url": "https://platform.claude.com/settings/keys",
     "models": ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"],
     "options": {"check": "chat", "no_temperature": True}},
    {"id": "gemini", "name": "Google Gemini", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
     "key_url": "https://aistudio.google.com/apikey", "models": ["gemini-2.5-flash", "gemini-2.5-pro"], "options": {}},
    {"id": "openrouter", "name": "OpenRouter", "base_url": "https://openrouter.ai/api/v1",
     "key_url": "https://openrouter.ai/keys", "models": ["openai/gpt-5-mini", "anthropic/claude-sonnet-5-5"],
     "options": {"headers": {"X-Title": "CiciByte AI Media Factory"}}},
    {"id": "groq", "name": "Groq", "base_url": "https://api.groq.com/openai/v1",
     "key_url": "https://console.groq.com/keys", "models": ["llama-3.3-70b-versatile"], "options": {}},
    {"id": "deepseek", "name": "DeepSeek", "base_url": "https://api.deepseek.com/v1",
     "key_url": "https://platform.deepseek.com/api_keys", "models": ["deepseek-chat"], "options": {}},
    {"id": "mistral", "name": "Mistral", "base_url": "https://api.mistral.ai/v1",
     "key_url": "https://console.mistral.ai/api-keys", "models": ["mistral-large-latest", "mistral-small-latest"], "options": {}},
    {"id": "xai", "name": "xAI (Grok)", "base_url": "https://api.x.ai/v1",
     "key_url": "https://console.x.ai", "models": ["grok-4"], "options": {}},
]  # fmt: skip

BY_ID = {p["id"]: p for p in PRESETS}


def get(preset_id: str) -> dict | None:
    return BY_ID.get(preset_id)
