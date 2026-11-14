#!/usr/bin/env bash
# Dump the database to ./backups/mf-YYYYmmdd-HHMMSS.sql.gz and keep the newest $KEEP (default 14) dumps.
# A failed dump never leaves a backup-looking file behind and never rotates out good backups.
set -euo pipefail
cd "$(dirname "$0")/.."
KEEP="${KEEP:-14}"
mkdir -p backups
out="backups/mf-$(date +%Y%m%d-%H%M%S).sql.gz"
tmp="$out.tmp"
trap 'rm -f "$tmp"' EXIT

docker compose -f deploy/docker-compose.yml --env-file .env exec -T db pg_dump -U mf -d mf --clean --if-exists \
  | gzip > "$tmp"

gzip -t "$tmp" || { echo "backup failed: corrupt archive" >&2; exit 1; }
gunzip -c "$tmp" | tail -n 5 | grep -q "PostgreSQL database dump complete" \
  || { echo "backup failed: dump incomplete" >&2; exit 1; }

mv "$tmp" "$out"
echo "backup written: $out"
ls -1t backups/mf-*.sql.gz | tail -n +"$((KEEP + 1))" | xargs -r rm -f
