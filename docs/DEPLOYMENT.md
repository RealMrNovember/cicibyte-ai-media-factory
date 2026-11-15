# Deployment / Kurulum

CiciByte AI Media Factory runs as three Docker containers: `db` (PostgreSQL 16), `api` (REST API + panel)
and `worker` (production queue). Everything lives in two volumes: `mf_pg` (database) and `mf_data`
(media, models).

## Requirements / Gereksinimler

- Linux server (Ubuntu/Debian recommended) or any host with **Docker Engine** and **Docker Compose v2**
- 4+ CPU cores, 8 GB+ RAM (more for local LLM/TTS), 50 GB+ free disk
- `git`, `curl`

## Install / Kurulum

Install [Tailscale](https://tailscale.com) on the server first (recommended), then:

```bash
git clone https://github.com/RealMrNovember/cicibyte-ai-media-factory.git
cd cicibyte-ai-media-factory
bash deploy/install.sh
```

The script:

1. creates `.env` with a random `MF_SECRET_KEY` and database password (never overwrites an existing `.env`),
2. publishes the panel on this machine's **Tailscale address** if Tailscale is running (otherwise on
   `127.0.0.1` only) and allows its tailnet names in `MF_ALLOWED_HOSTS`,
3. builds the image and starts `db`, `api`, `worker`, then waits for `GET /api/health`,
4. prints the address to enter in the desktop app (**Settings → Server**), e.g. `http://my-server:8080`.

> ⚠️ **There is no sign-in.** Anyone who can reach the port controls the factory. Keep it on a private
> network (Tailscale or your LAN) and **never expose it to the internet** — no port forwarding, no
> `tailscale funnel`.

### Desktop app

Download the Windows installer from https://mediafactory.cicibyte.com, install it, open **Settings → Server**
and enter the address printed by `install.sh`. All heavy work runs on the server; the app only shows the panel.

### Other networks

- **LAN only:** set `MF_PUBLISH_ADDR=192.168.1.20` (the server's LAN address) and add that address and the
  server's name to `MF_ALLOWED_HOSTS`, then `docker compose -f deploy/docker-compose.yml --env-file .env up -d`.
- **Behind a reverse proxy with its own authentication** (VPN, SSO, IP allow-list): keep
  `MF_PUBLISH_ADDR=127.0.0.1`, proxy to `127.0.0.1:8080`, allow request bodies up to 2 GB on
  `/api/backgrounds` (clip uploads) and add the proxy host name to `MF_ALLOWED_HOSTS`.

`MF_ALLOWED_HOSTS` is a safety check against DNS-rebinding attacks from web pages; list only the names you use.

## YouTube

Each installation uses its own Google OAuth client:

1. In Google Cloud Console create a project and enable **YouTube Data API v3**.
2. Configure the **OAuth consent screen** (External) and add your Google account under *Test users*.
3. Create **Credentials → OAuth client ID → Desktop app**.
4. In the app open **Settings → YouTube**, paste the client ID and secret, save, then **Connect a channel**.
   Google sign-in opens in your normal browser and returns to the app.

Videos can be sent from **Ready videos** (now or at a chosen time; YouTube publishes scheduled videos itself)
or by a publishing schedule under **Schedule**. Google may keep videos uploaded by an unverified app private
until the app passes Google's audit.

**Limits and extras.** Each channel in Settings → YouTube has an *uploads per day* limit (default 6, 0 = none)
and an optional playlist (paste its link) that every upload is added to. Each upload also sends the subtitle
file as a caption track. The server counts the YouTube API quota it spends (upload 1,600 units, captions 400,
cover and playlist 50 each; 10,000 per day unless Google raised yours — set `MF_YOUTUBE_DAILY_QUOTA`). When a
channel's limit or the quota is reached, uploads wait and go out automatically after midnight Pacific time,
when Google resets the quota. If Google withdraws a channel's access, the channel shows a warning with a
**Reconnect** button. Channels connected before captions and playlists were added need one reconnect for them.

## Instagram

Reels are published with the official **Instagram API with Instagram Login**. It works only for a
**professional account** (Creator or Business); switching is free in Instagram → Settings → Account type.

1. At https://developers.facebook.com create an app (type *Business*) and add the product **Instagram →
   API setup with Instagram login**.
2. Add your Instagram account there and press **Generate token**.
3. In the app open **Settings → Instagram**, paste the token and press **Connect**.

The token lasts 60 days; the server renews it by itself (weekly and before it runs out). The video is sent
straight from the server (resumable upload), so the server does not need a public address. In **Ready videos**
use **Publish** and tick YouTube, Instagram or both; schedules and autopilot have the same choice. With both,
YouTube uploads first and Instagram follows. Instagram has no scheduled publishing in its API, so a scheduled
Reel waits on the server and is sent at that time. Instagram allows about 50 API posts per 24 hours.

**Personal accounts** cannot publish through the API (Instagram does not allow it). For them each video has
**Share on Instagram manually**: download the video, copy the ready caption, post it in Instagram, then mark it
as shared.

## Automatic updates

Turn them on once (as root, from the repository checkout):

```bash
sudo bash deploy/update/install-autoupdate.sh                         # bare metal (systemd)
sudo MF_UPDATE_MODE=docker bash deploy/update/install-autoupdate.sh   # docker compose
```

Every 30 minutes the server checks the `main` branch on GitHub. When there is a new commit it installs it, runs
the database migrations, restarts the services and checks `/api/health`. If the new version does not come up
healthy it goes back to the previous commit. Updates wait while a video is being produced.
**Settings → Updates** shows the running version, the latest commit, the status and the log, and lets you turn
automatic updates off or press **Check & update now**.

The desktop app updates itself from GitHub Releases: when a newer release exists, a banner offers **Update now**.
The installer is only accepted from this repository's releases and only when its SHA-256 matches the published
`.sha256` file.

## Moving settings to another computer

**Settings → Backup & move → Export settings** writes AI providers (with keys), task routes, sources, schedules,
YouTube and Reddit settings to a JSON file. Keys are only included when you set a password; they are encrypted
with it. On the other computer or server use **Import** with the same password. Import adds and updates by
name and never deletes. Videos, clips and music are not part of the file.

## Source collection

The worker collects enabled sources on their own schedule (default every 60 minutes; failing sources back
off up to 24 hours). Source fetching refuses private/internal addresses; to allow a specific internal host,
add it to `.env`:

```
MF_FETCH_ALLOWLIST=["wiki.lan"]
```

For the official Reddit API, create a *script* app at https://www.reddit.com/prefs/apps and enter its client
id and secret in Settings → Reddit (stored encrypted). Without it, use the
`reddit_rss` adapter.

## Script Doctor

Each new script is graded 1–10 by the same `script` AI route. Scripts under 7 (or far from the target
length) are rewritten once with the reviewer's notes, and the better version is kept. The score shows in
the job details. This costs up to three extra AI calls per script; to turn it off, add to `.env`:

```
MF_SCRIPT_DOCTOR=false
```

## Originality check

After rendering, the narration is compared with the source story. If more than 15% of its 5-word phrases
also appear in the source, or 12 or more words are copied in a row, the quality check fails: the video
waits in Ready for a person even when a schedule auto-approves or auto-publishes. Your own stories (AI
stories you add) are not checked. Copying through translation is not detected.

## Sound effects and video format

**Studio → Music → Sound effects** adds short effects where the story mentions them: knocks, creaks,
heartbeat, clock ticks, whispers, thunder and an impact on screams or slams (English and Turkish words), plus
a whoosh under the opening line. Effects are at least 3 seconds apart, at most 6 per video, and sit on top of
the narration and music at their own volume. They are synthesised by ffmpeg, so there is no copyright in them.
To use your own recordings, put audio files in `DATA_DIR/media/sfx` with the effect's name in the file name
(`knock`, `creak`, `heartbeat`, `tick`, `whisper`, `thunder`, `hit`, `whoosh`, e.g. `old-door-knock.wav`).

**Studio → Captions → Format** switches between 9:16 (1080×1920, Shorts and Reels) and 16:9 (1920×1080,
a regular YouTube video). Captions are scaled for the wide frame, the cover becomes 1280×720, the quality
check expects the chosen size and YouTube uploads of 16:9 videos are not tagged `#shorts`.

## Channels & concepts

**Schedule → Channels & concepts** stores one recipe per channel: language, topic, length, caption style,
voice and music (taken from your current Studio settings), the YouTube channel, platforms (YouTube and/or
Instagram) and visibility. **Make one now** produces a video with it. Autopilot and publishing schedules can
*follow a concept*: autopilot then makes and publishes with the concept's recipe and channel, and a publishing
schedule sends only that concept's approved videos.

A **stock target** keeps that many of the concept's videos ready (queued, waiting for review or approved).
Every 10 minutes the server tops up concepts below their target, at most two new videos at a time, from
unused stories in the concept's language and topic. With "approve automatically" on, stock videos that pass
the quality check are approved and a publishing schedule can send them; otherwise they wait for you.
Concepts are part of the settings backup.

## Sensitive content and rights check

After the script is written, the AI (task route `classify`; the `script` route is used when `classify` is not
set up) checks the narration for what YouTube and Instagram restrict: harm to minors, sexual content,
self-harm, hate, dangerous instructions, very graphic gore and real recent tragedies. Horror itself is fine.
The first five always fail the quality check; gore and real tragedies fail only when severe. A source whose
rights are set to *restricted* also fails. A failed check never stops the video: it waits in Ready for you,
even on autopilot. If the AI cannot run the check, the video also waits for review.

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

## Logs

```bash
docker compose -f deploy/docker-compose.yml --env-file .env logs -f api worker
```

---

Powered by [CiciByte Technology](https://cicibyte.com) · [Buy me a coffee](https://buymeacoffee.com/mikeross)
