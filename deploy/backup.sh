#!/usr/bin/env bash
# Dump the database to ./backups/mf-YYYYmmdd-HHMM.sql.gz and keep the newest 14 dumps.
set -euo pipefail
cd "$(dirname "$0")/.."
KEEP="${KEEP:-14}"
mkdir -p backups
out="backups/mf-$(date +%Y%m%d-%H%M%S).sql.gz"
docker compose -f deploy/docker-compose.yml --env-file .env exec -T db pg_dump -U mf -d mf --clean --if-exists | gzip > "$out"
[ -s "$out" ] || { echo "backup failed: empty file" >&2; rm -f "$out"; exit 1; }
echo "backup written: $out"
ls -1t backups/mf-*.sql.gz | tail -n +"$((KEEP + 1))" | xargs -r rm -f
