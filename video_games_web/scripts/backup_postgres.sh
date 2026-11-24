#!/bin/sh
# Copia de seguridad periodica de PostgreSQL (por defecto, una vez al dia).
set -u

INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"
DIR="${BACKUP_DIR:-/backups}"
HOST="${POSTGRES_HOST:-postgres}"
USER="${POSTGRES_USER:-vguser}"
DB="${POSTGRES_DB:-video_games}"

mkdir -p "$DIR"
export PGPASSWORD="${POSTGRES_PASSWORD:-vgpass}"

dump_once() {
  ts=$(date -u +%Y%m%dT%H%M%SZ)
  file="$DIR/${DB}_${ts}.dump"
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) backup start $file"
  if pg_dump -h "$HOST" -U "$USER" -d "$DB" -Fc -f "$file"; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) backup ok $file"
  else
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) backup failed" >&2
    rm -f "$file"
  fi
  find "$DIR" -name '*.dump' -type f -mtime "+${KEEP_DAYS}" -delete 2>/dev/null || true
}

dump_once
while true; do
  sleep "$INTERVAL"
  dump_once
done
