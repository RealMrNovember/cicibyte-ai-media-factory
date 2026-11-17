# CiciByte AI Media Factory

[![Powered by CiciByte Technology](https://img.shields.io/badge/Powered%20by-CiciByte%20Technology-111111)](https://cicibyte.com)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-FFDD00?logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/mikeross)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Open-source AI short-video factory that runs on your computer.** Collect stories and articles from
sources you manage, turn them into original scripts with the AI you connect, generate voice, captions and
video locally, and publish to YouTube, Instagram and TikTok — only after you approve.

> 🇹🇷 **Kendi bilgisayarında çalışan, açık kaynak AI kısa video fabrikası.** Yönettiğin kaynaklardan
> içerik toplar, bağladığın yapay zekâ ile özgün senaryoya çevirir, sesi, altyazıyı ve videoyu yerelde
> üretir; senin onayınla YouTube, Instagram ve TikTok'ta yayınlar.

## Highlights

- **Your sources, fully managed:** Reddit, RSS/Atom, web pages, your own files — add, edit, pause, remove.
- **Bring your own AI:** Easy Setup finds the AI on your computer (Ollama, LM Studio, Jan, llama.cpp…),
  connects your own AI server, or an AI service with your API key (OpenAI, Anthropic, Gemini, OpenRouter,
  Groq, DeepSeek, Mistral, xAI). Per-task ordered fallback with retries.
- **Local-first:** runs on CPU, no paid API required.
- **Multi-channel, multi-concept, multi-language** (English and Turkish).
- **Human-approved publishing:** uploads are private by default; nothing is published without your approval.
- **YouTube and Instagram:** publish a video to YouTube Shorts, Instagram Reels or both, now, at a set time or
  on autopilot. Instagram publishing needs a professional (Creator/Business) account; personal accounts get a
  one-click manual share (video + ready caption).
- **TikTok:** send videos to your TikTok inbox as drafts (you post them from the app) or, once TikTok has
  approved your developer app, post them directly. Without a connection there is a manual share as well.
- **Source- and rights-aware:** every item keeps its source, hash and rights status.

## Quick start

1. Download the app from **[mediafactory.cicibyte.com](https://mediafactory.cicibyte.com)** (Windows) and
   install it. No server, Docker or account is needed: the whole engine runs inside the app.
2. On first start **Easy Setup** downloads the voices and the caption model and connects your AI.
3. Make your first video in the Studio, then connect YouTube, Instagram or TikTok in Settings.

macOS and Linux: the local engine is coming in a next release; until then their apps connect to a server.

### Advanced: run it as a server

For a shared machine or a home server (and for macOS/Linux today):

```bash
git clone https://github.com/RealMrNovember/cicibyte-ai-media-factory.git
cd cicibyte-ai-media-factory
bash deploy/install.sh
```

Requires Docker + Compose v2. The installer asks who may reach it (this machine, your local network or a
Tailscale network). In the app choose Settings → App → "On my Media Factory server". See
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for updates and backups.

## Sources

Add, edit, pause and remove sources from the panel or the API:

| Adapter | What it collects |
|---|---|
| `reddit_rss` | A subreddit's public feed (sort, time range, minimum length, NSFW filter); no credentials needed |
| `reddit` | The official Reddit API (adds minimum score); register an app and add it under Settings → Source credentials |
| `rss` | Any RSS/Atom feed |
| `web` | A single web page (respects robots.txt) |
| manual | Paste text, a URL or upload `.txt`, `.md`, `.pdf`, `.docx` (up to 10 MB) |

Items are deduplicated, keep their provenance and start with rights status `unknown`.
See [docs/SOURCE_RIGHTS.md](docs/SOURCE_RIGHTS.md).

## Status

v0.5: the Windows app runs everything on your computer, with Easy Setup for the AI. The full pipeline runs — sources, AI script with self-review, originality and sensitive-content checks,
voice (Piper, Chatterbox and voice cloning), captions, music and sound effects, 9:16 or 16:9 rendering,
cover and quality check — plus YouTube and Instagram publishing, schedules, autopilot, channel concepts and the
Windows app. See [ROADMAP.md](ROADMAP.md).

Docs: [Deployment](docs/DEPLOYMENT.md) · [Operations](docs/OPERATIONS.md) · [Security](SECURITY.md) ·
[Source rights](docs/SOURCE_RIGHTS.md)

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
