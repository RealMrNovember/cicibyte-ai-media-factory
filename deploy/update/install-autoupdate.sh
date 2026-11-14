#!/usr/bin/env bash
# Turn on automatic updates (run as root from the repository checkout).
#   bare metal: bash deploy/update/install-autoupdate.sh
#   docker:     MF_UPDATE_MODE=docker bash deploy/update/install-autoupdate.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$(cd "$HERE/../.." && pwd)"
MODE="${MF_UPDATE_MODE:-systemd}"
DIR="${MF_UPDATE_DIR:-/var/lib/mediafactory/data/update}"
[ "$(id -u)" = 0 ] || { echo "run as root" >&2; exit 1; }
git -C "$SRC" rev-parse --git-dir >/dev/null 2>&1 || { echo "$SRC must be a git clone of the repository" >&2; exit 1; }

install -m 0755 "$HERE/mf-update.sh" /usr/local/sbin/mf-update
mkdir -p /etc/mediafactory "$DIR"
cat > /etc/mediafactory/update.env <<CONF
MF_UPDATE_MODE=$MODE
MF_SRC=$SRC
MF_UPDATE_DIR=$DIR
MF_BRANCH=${MF_BRANCH:-main}
${MF_HEALTH_URL:+MF_HEALTH_URL=$MF_HEALTH_URL}
CONF
id mf >/dev/null 2>&1 && chown mf:mf "$DIR" || true
sed "s#/var/lib/mediafactory/data/update#$DIR#" "$HERE/mf-update.path" > /etc/systemd/system/mf-update.path
install -m 0644 "$HERE/mf-update.service" "$HERE/mf-update.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now mf-update.timer mf-update.path
echo "Automatic updates are on: checks every 30 minutes; status in $DIR/update-status.json"
