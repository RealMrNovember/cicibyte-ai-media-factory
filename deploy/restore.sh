#!/usr/bin/env bash
# Restore a dump made by backup.sh. Usage: bash deploy/restore.sh backups/mf-YYYYmmdd-HHMMSS.sql.gz
# Runs in a single transaction: on any error nothing is changed. api and worker are always restarted.
set -euo pipefail
cd "$(dirname "$0")/.."
file="${1:?usage: restore.sh <backup.sql.gz>}"
[ -f "$file" ] || { echo "no such file: $file" >&2; exit 1; }
gzip -t "$file" || { echo "not a valid gzip archive: $file" >&2; exit 1; }
COMPOSE=(docker compose -f deploy/docker-compose.yml --env-file .env)

if [ "${YES:-}" != "1" ]; then
  read -r -p "This replaces ALL current data with $file. Type 'restore' to continue: " answer
  [ "$answer" = "restore" ] || { echo "aborted"; exit 1; }
fi

echo "taking a safety backup of the current data first..."
bash deploy/backup.sh

trap '"${COMPOSE[@]}" start api worker >/dev/null' EXIT
"${COMPOSE[@]}" stop api worker
gunzip -c "$file" | "${COMPOSE[@]}" exec -T db psql -U mf -d mf -v ON_ERROR_STOP=1 --single-transaction -q
echo "restored from $file"
