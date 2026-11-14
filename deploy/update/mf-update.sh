#!/usr/bin/env bash
# CiciByte AI Media Factory — automatic updates from GitHub.
#
# Checks the branch on GitHub; when there is a new commit (and updates are allowed) it installs it, runs the
# database migrations, restarts the services and checks health. If the new version does not come up healthy,
# it goes back to the previous commit. Updates wait while a video is being produced.
#
# Modes (MF_UPDATE_MODE):
#   systemd (default) — bare-metal install: /opt/mediafactory/{src,venv}, services mf-api and mf-worker
#   docker            — docker compose install: the repository checkout is MF_SRC
#
# Files in MF_UPDATE_DIR (shared with the app, which shows them in Settings → Updates):
#   update-config.json  {"auto": true|false}          written by the app
#   update-request      present = "update now" (content "force" = do not wait for running jobs)
#   update-status.json  written here
set -uo pipefail

MODE="${MF_UPDATE_MODE:-systemd}"
SRC="${MF_SRC:-/opt/mediafactory/src}"
VENV="${MF_VENV:-/opt/mediafactory/venv}"
ENV_FILE="${MF_ENV_FILE:-/etc/mediafactory/env}"
DIR="${MF_UPDATE_DIR:-/var/lib/mediafactory/data/update}"
BRANCH="${MF_BRANCH:-main}"
HEALTH_URL="${MF_HEALTH_URL:-http://127.0.0.1:8080/api/health}"
APP_USER="${MF_APP_USER:-mf}"
COMPOSE=(docker compose -f deploy/docker-compose.yml --env-file .env)

mkdir -p "$DIR"
STATUS="$DIR/update-status.json"
LOG="$DIR/update.log"
exec 9>"$DIR/.lock"
flock -n 9 || { echo "another update is running"; exit 0; }

log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }

status() { # status <state> <message> [current] [latest]
  python3 - "$STATUS" "$1" "$2" "${3:-}" "${4:-}" "$BRANCH" <<'PY'
import json, sys, datetime, os
path, state, msg, cur, latest, branch = sys.argv[1:7]
old = {}
try:
    old = json.load(open(path))
except Exception:
    pass
now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
data = {**old, "state": state, "message": msg, "branch": branch, "checked_at": now}
if cur:
    data["current"] = cur
if latest:
    data["latest"] = latest
if state in ("updated", "rolled_back", "failed"):
    data["last_update_at"] = now
tmp = path + ".tmp"
json.dump(data, open(tmp, "w"), indent=2)
os.chmod(tmp, 0o644)
os.replace(tmp, path)
PY
}

auto_enabled() {
  python3 -c "import json,sys; print('true' if json.load(open(sys.argv[1])).get('auto', True) else 'false')" \
    "$DIR/update-config.json" 2>/dev/null || echo true
}

as_app() { # run an `mf` command as the app user with the app environment
  if [ "$MODE" = docker ]; then
    (cd "$SRC" && "${COMPOSE[@]}" exec -T api "$@")
  else
    (set -a; . "$ENV_FILE"; set +a; cd /tmp && runuser -u "$APP_USER" -- "$VENV/bin/$1" "${@:2}")
  fi
}

healthy() {
  for _ in $(seq 1 45); do
    curl -fsS -m 3 "$HEALTH_URL" >/dev/null 2>&1 && return 0
    sleep 2
  done
  return 1
}

install_and_restart() {
  if [ "$MODE" = docker ]; then
    (cd "$SRC" && "${COMPOSE[@]}" up -d --build >>"$LOG" 2>&1)
    return $?
  fi
  "$VENV/bin/pip" install -q "$SRC" >>"$LOG" 2>&1 || return 1
  as_app mf migrate >>"$LOG" 2>&1 || return 1
  install -m 0755 "$SRC/deploy/update/mf-update.sh" /usr/local/sbin/mf-update  # next run uses the new updater
  systemctl restart mf-api mf-worker
}

TRIGGER=timer FORCE=no
if [ -f "$DIR/update-request" ]; then
  TRIGGER=manual
  grep -q force "$DIR/update-request" 2>/dev/null && FORCE=yes
  rm -f "$DIR/update-request"
fi

cd "$SRC" || { status failed "source folder $SRC not found"; exit 1; }
git config --global --add safe.directory "$SRC" 2>/dev/null || true
CUR="$(git rev-parse HEAD)"
if ! git fetch -q origin "$BRANCH" 2>>"$LOG"; then
  status error "could not reach GitHub" "$CUR"
  exit 1
fi
NEW="$(git rev-parse "origin/$BRANCH")"

if [ "$CUR" = "$NEW" ]; then
  status up_to_date "already on the latest version" "$CUR" "$NEW"
  exit 0
fi
if [ "$TRIGGER" = timer ] && [ "$(auto_enabled)" != true ]; then
  status available "a new version is available (automatic updates are off)" "$CUR" "$NEW"
  exit 0
fi
if [ "$FORCE" != yes ] && ! as_app mf busy >/dev/null 2>&1; then
  status deferred "waiting for running jobs to finish; will retry" "$CUR" "$NEW"
  log "deferred: jobs running"
  exit 0
fi

log "updating ${CUR:0:7} -> ${NEW:0:7} ($TRIGGER)"
status updating "installing ${NEW:0:7}" "$CUR" "$NEW"
git reset -q --hard "$NEW"
if install_and_restart && healthy; then
  status updated "updated to ${NEW:0:7}" "$NEW" "$NEW"
  log "updated to ${NEW:0:7}"
  exit 0
fi

log "new version unhealthy; rolling back to ${CUR:0:7}"
git reset -q --hard "$CUR"
if install_and_restart && healthy; then
  status rolled_back "update to ${NEW:0:7} failed its health check; back on ${CUR:0:7}" "$CUR" "$NEW"
else
  status failed "update failed and the rollback is unhealthy too — check $LOG" "$CUR" "$NEW"
fi
exit 1
