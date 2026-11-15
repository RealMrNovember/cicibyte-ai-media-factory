# Operations / İşletim

Day-to-day running of a CiciByte AI Media Factory server: what runs where, routine care and how to fix the
usual problems. Installation is in [DEPLOYMENT.md](DEPLOYMENT.md).

## What runs where

| Part | Docker install | Bare-metal install |
|---|---|---|
| API + panel | container `api` | service `mf-api` (`/opt/mediafactory/venv`, source in `/opt/mediafactory/src`) |
| Production queue, schedules, stock keeper | container `worker` | service `mf-worker` |
| Database | container `db` (PostgreSQL 16), volume `mf_pg` | local PostgreSQL |
| Media, models, voices, videos | volume `mf_data` (`/data`) | `MF_DATA_DIR`, e.g. `/var/lib/mediafactory/data` |
| Settings | `.env` in the checkout | `/etc/mediafactory/env` |

Everything heavy (AI calls, voice, captions, rendering, uploads) runs on the server. The desktop app only shows
the panel.

Inside the data folder:

| Folder | Content |
|---|---|
| `videos/` | one folder per video: `short.mp4`, `thumbnail.jpg`, captions, `script.json`, `result.json` |
| `media/backgrounds`, `media/music`, `media/sfx`, `media/voices` | your clips, music, sound effects and cloned voices |
| `models/` | downloaded Piper voices and whisper models |
| `update/` | automatic update state and log |

## Health checks

- `GET /api/health` answers `{"status":"ok"}` when the API and the database are up.
- **Overview** and **Live** in the panel show running and failed jobs; **Production** has each job's log.
- `mf busy` (bare metal) exits 0 while a video is being made — the updater uses it to wait.
- Logs: `docker compose -f deploy/docker-compose.yml --env-file .env logs -f api worker`, or
  `journalctl -u mf-api -u mf-worker -f` on bare metal.

## Routine care

| When | What |
|---|---|
| Daily | Backups: `bash deploy/backup.sh` from cron (keeps the newest 14). Keep a copy of `.env` / `/etc/mediafactory/env` elsewhere: without `MF_SECRET_KEY` the stored keys and tokens cannot be decrypted. |
| Weekly | Check **Settings → YouTube** (reconnect warnings, quota) and **Settings → Instagram** (token expiry date). |
| Monthly | Free disk space: delete old folders under `videos/` you no longer need (published videos stay on YouTube/Instagram). |
| After moving | Export settings with a password on the old server, import on the new one (**Settings → Backup & move**). |

Updates install themselves from GitHub when automatic updates are on (**Settings → Updates**); a version that does
not start healthy is rolled back. Manual update: see DEPLOYMENT.md.

## Common problems

| Symptom | Cause and fix |
|---|---|
| Scripts fail with "all AI providers failed" | Every step of the `script` route failed. Check **Settings → AI providers → Test**, keys and the router. Add a local model as the last step so production never stops. |
| Script step is slow | The cloud models failed and the local fallback is running on CPU. Normal for a local model; check the cloud providers. |
| "estimated timing" in the caption step | faster-whisper could not run (first model download, memory). Captions still work with estimated timing. |
| Video waits with "quality check failed" | Open the QC badge: length, loudness, silence, originality (copied from the source) or sensitive content. Edit & remake, or approve it yourself. |
| YouTube: "Waiting for YouTube's daily limit" | The channel's daily limit or the API quota is reached. It uploads by itself after midnight Pacific time. Raise the channel limit, or `MF_YOUTUBE_DAILY_QUOTA` if Google raised your quota. |
| YouTube: "reconnect this channel" | Google withdrew access (password change, access removed, unverified app tokens expire). Press **Reconnect**. |
| Cover, captions or playlist not added | Custom covers need a verified channel; captions and playlists need a reconnect for channels connected before they existed. The video itself is uploaded. |
| Instagram: "token has expired" | It was not renewed for 60 days (server off). Generate a new token in Meta and paste it in **Settings → Instagram**. |
| Instagram: "personal account" | The API only publishes for Creator or Business accounts. Switch for free, or use **Share manually**. |
| Reddit sources fail with 403/429 | Reddit blocks anonymous requests from servers. Add a Reddit API app in **Settings → Reddit**. |
| Voice cloning / Chatterbox slow or out of memory | Chatterbox needs about 5 GB RAM. The model unloads when idle or when memory is low; give the server more RAM or use Piper voices. |
| A job is stuck in "running" | A worker that disappears is detected by its heartbeat and the stage is retried. Restart the worker if it does not recover in a few minutes; **Retry** a failed job from Production. |
| The panel says "Cannot reach the server" | Check the address in **Settings → Server**, Tailscale on both machines, and that `MF_ALLOWED_HOSTS` contains the name you use. |

## Restore

```bash
bash deploy/restore.sh backups/mf-YYYYmmdd-HHMMSS.sql.gz   # replaces all data, asks first
```

Restore the same `MF_SECRET_KEY` the backup was made with, or re-enter keys and reconnect channels afterwards.

---

Powered by [CiciByte Technology](https://cicibyte.com)
