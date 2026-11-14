# Deployment / Kurulum

CiciByte AI Media Factory runs as three Docker containers: `db` (PostgreSQL 16), `api` (REST API + panel)
and `worker` (production queue). Everything lives in two volumes: `mf_pg` (database) and `mf_data`
(media, models).

## Requirements / Gereksinimler

- Linux server (Ubuntu/Debian recommended) or any host with **Docker Engine** and **Docker Compose v2**
- 4+ CPU cores, 8 GB+ RAM (more for local LLM/TTS), 50 GB+ free disk
- `git`, `curl`

## Install / Kurulum

```bash
git clone https://github.com/RealMrNovember/cicibyte-ai-media-factory.git
cd cicibyte-ai-media-factory
bash deploy/install.sh you@example.com
```

The script:

1. creates `.env` with a random `MF_SECRET_KEY` and database password (never overwrites an existing `.env`),
2. builds the image and starts `db`, `api`, `worker`,
3. waits for `GET /api/health`,
4. creates the admin account and **prints its password once** — store it safely.

The panel listens on **`127.0.0.1:8080` only** (change with `MF_BIND_PORT` in `.env`).

> ⚠️ **Do not expose the panel directly to the internet.** Use Tailscale (recommended) or a reverse
> proxy with HTTPS.

### Remote access with Tailscale (recommended)

Install Tailscale on the server, then either open `http://<server>:8080` through an SSH tunnel or serve it
on your tailnet only:

```bash
sudo tailscale serve --bg 8080
```

Add the tailnet host name to `MF_ALLOWED_HOSTS` in `.env`, e.g.
`MF_ALLOWED_HOSTS=["localhost","127.0.0.1","media.tail1234.ts.net"]`, then
`docker compose -f deploy/docker-compose.yml --env-file .env up -d`.
Never use `tailscale funnel` for the panel — that publishes it to the internet.

### Reverse proxy (Caddy example)

```
media.example.com {
    reverse_proxy 127.0.0.1:8080
}
```

Restrict access (VPN/IP allow-list) and add `media.example.com` to `MF_ALLOWED_HOSTS`.

## Update / Güncelleme

```bash
git pull
docker compose -f deploy/docker-compose.yml --env-file .env up -d --build
```

Migrations run automatically when `api` starts. Take a backup first.

## Backup & restore / Yedekleme

```bash
bash deploy/backup.sh                      # -> backups/mf-YYYYmmdd-HHMMSS.sql.gz (keeps newest 14)
bash deploy/restore.sh backups/mf-....sql.gz   # asks for confirmation, replaces all data
```

Schedule backups with cron, e.g. `30 3 * * * cd /opt/mediafactory && bash deploy/backup.sh`.
Back up `.env` separately and securely: without `MF_SECRET_KEY` stored API keys and OAuth tokens cannot
be decrypted.

## Admin password reset

```bash
docker compose -f deploy/docker-compose.yml --env-file .env exec api mf create-admin --email you@example.com --reset
```

## Logs

```bash
docker compose -f deploy/docker-compose.yml --env-file .env logs -f api worker
```

---

Powered by [CiciByte Technology](https://cicibyte.com) · [Buy me a coffee](https://buymeacoffee.com/mikeross)
