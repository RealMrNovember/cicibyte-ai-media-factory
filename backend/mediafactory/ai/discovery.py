"""Find AI servers running on this computer (127.0.0.1 only, known ports only — not a general scanner)."""

import re
from concurrent.futures import ThreadPoolExecutor

import httpx

# (tool id, display name, port). Several tools may share a port; the first that answers there is reported.
TOOLS: list[tuple[str, str, int]] = [
    ("ollama", "Ollama", 11434),
    ("lmstudio", "LM Studio", 1234),
    ("jan", "Jan", 1337),
    ("llamacpp", "llama.cpp / LocalAI", 8080),
    ("koboldcpp", "KoboldCpp", 5001),
    ("vllm", "vLLM", 8000),
    ("textgen", "text-generation-webui", 5000),
    ("gpt4all", "GPT4All", 4891),
]
NAMES = {t: n for t, n, _ in TOOLS}
PROBE_TIMEOUT_S = 0.4
DOWNLOADS = {"ollama": "https://ollama.com/download", "lmstudio": "https://lmstudio.ai/download"}


def _models(c: httpx.Client, base: str) -> list[str] | None:
    try:
        r = c.get(f"{base}/models")
        if r.status_code != 200:
            return None
        data = r.json().get("data")
        return [str(m["id"]) for m in data if isinstance(m, dict) and m.get("id")] if isinstance(data, list) else None
    except (httpx.HTTPError, ValueError, AttributeError, TypeError):
        return None


def _probe(tool: str, port: int, host: str, http: httpx.Client | None) -> dict | None:
    c = http or httpx.Client(timeout=PROBE_TIMEOUT_S)
    root = f"http://{host}:{port}"
    if tool == "ollama":
        try:
            if c.get(f"{root}/api/version").status_code != 200:
                return None
        except httpx.HTTPError:
            return None
    models = _models(c, f"{root}/v1")
    if models is None:
        return None
    return {"tool": tool, "name": NAMES[tool], "base_url": f"{root}/v1", "models": rank(models)}


def scan(host: str = "127.0.0.1", *, http: httpx.Client | None = None) -> list[dict]:
    with ThreadPoolExecutor(max_workers=len(TOOLS)) as pool:
        results = list(pool.map(lambda t: _probe(t[0], t[2], host, http), TOOLS))
    found, ports = [], set()
    for (_, _, port), res in zip(TOOLS, results, strict=True):
        if res and port not in ports:
            found.append(res)
            ports.add(port)
    return found


_SKIP = re.compile(r"embed|rerank|whisper|tts|vision-only|clip", re.I)


def _size(name: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)\s*b\b", name.lower().replace(":", " ").replace("-", " "))
    return float(m.group(1)) if m else 0.0


def rank(models: list[str]) -> list[str]:
    """Chat models first, bigger first, "instruct"/"chat" preferred; embeddings and the like last."""
    def key(name: str):
        return (bool(_SKIP.search(name)), -_size(name), not re.search(r"instruct|chat|it\b", name, re.I), name)

    return sorted(models, key=key)


def normalize_base(url: str) -> str:
    """Accept what people paste: no scheme, a bare Ollama address, a trailing slash."""
    url = (url or "").strip().rstrip("/")
    if url and "://" not in url:
        url = "http://" + url
    if url and not re.search(r"/v\d+(beta)?(/openai)?$", url) and not url.endswith("/api/v1"):
        url += "/v1"
    return url
