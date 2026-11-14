# CiciByte AI Media Factory

[![Powered by CiciByte Technology](https://img.shields.io/badge/Powered%20by-CiciByte%20Technology-111111)](https://cicibyte.com)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-FFDD00?logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/mikeross)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Self-hosted, open-source AI YouTube media factory.** Collect stories and articles from sources you
manage, turn them into original scripts with the AI you connect, generate voice, captions and video
locally, and publish to multiple YouTube channels — only after you approve.

> 🇹🇷 **Kendi sunucuna kurulan, açık kaynak AI YouTube içerik fabrikası.** Yönettiğin kaynaklardan
> içerik toplar, bağladığın yapay zekâ ile özgün senaryoya çevirir, sesi, altyazıyı ve videoyu yerelde
> üretir; senin onayınla birden fazla YouTube kanalına yükler.

## Highlights

- **Your sources, fully managed:** Reddit, RSS/Atom, web pages, your own files — add, edit, pause, remove.
- **Bring your own AI:** Ollama, llama.cpp, any OpenAI-compatible endpoint (e.g. a router), or cloud APIs.
  Per-task ordered fallback with retries.
- **Local-first:** runs on CPU, no paid API required.
- **Multi-channel, multi-concept, multi-language** (English and Turkish).
- **Human-approved publishing:** uploads are private by default; nothing is published without your approval.
- **Source- and rights-aware:** every item keeps its source, hash and rights status.

## Quick start

```bash
git clone https://github.com/RealMrNovember/cicibyte-ai-media-factory.git
cd cicibyte-ai-media-factory
bash deploy/install.sh you@example.com
```

Requires Docker + Compose v2. The panel is bound to `127.0.0.1:8080`; see
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for Tailscale/reverse-proxy access, updates and backups.

## Status

Under active development (v0.1): the foundation (auth, AI provider routing, job queue, Docker install)
is in place; sources, the production pipeline, the panel and YouTube publishing are next.

## Development

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
docker compose -f deploy/docker-compose.test.yml up -d --wait   # throwaway PostgreSQL on 127.0.0.1:55432
.venv/bin/pytest -q
```

## Support

If this project helps you, consider [buying me a coffee](https://buymeacoffee.com/mikeross).

## License

MIT — see [LICENSE](LICENSE). Includes code adapted from
[purffle-shorts](https://github.com/Chamanrajragu/purffle-shorts) (MIT); see [NOTICE](NOTICE).

---

**Powered by [CiciByte Technology](https://cicibyte.com)** — *From Idea to Future. Your Corporate Digital Brain.*
