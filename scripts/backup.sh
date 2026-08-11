#!/usr/bin/env bash
# Bazanın gündəlik ehtiyat nüsxəsi. Cron-a yaz:
#   0 3 * * * cd ~/papermind && bash scripts/backup.sh >> ~/backup.log 2>&1
#
# Son 7 nüsxə saxlanılır, köhnələri silinir.

set -euo pipefail
cd "$(dirname "$0")/.."

DIR="${BACKUP_DIR:-$HOME/papermind-backups}"
KEEP="${BACKUP_KEEP:-7}"
COMPOSE="docker compose -f docker-compose.prod.yml"
[ -f docker-compose.prod.yml ] || COMPOSE="docker compose"

mkdir -p "$DIR"
FILE="$DIR/papermind-$(date +%F-%H%M).sql.gz"

set -a; [ -f .env ] && . ./.env; set +a
USER_DB="${POSTGRES_USER:-elmradari}"
NAME_DB="${POSTGRES_DB:-elmradari}"

echo "[$(date '+%F %T')] backup başlayır -> $FILE"
$COMPOSE exec -T postgres pg_dump -U "$USER_DB" "$NAME_DB" | gzip > "$FILE"

SIZE=$(du -h "$FILE" | cut -f1)
if [ ! -s "$FILE" ]; then
  echo "XƏTA: nüsxə boşdur, silinir"
  rm -f "$FILE"
  exit 1
fi
echo "[$(date '+%F %T')] hazırdır ($SIZE)"

# köhnə nüsxələri təmizlə
ls -1t "$DIR"/papermind-*.sql.gz 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r old; do
  rm -f "$old"
  echo "  silindi: $(basename "$old")"
done

echo "  saxlanılan nüsxə sayı: $(ls -1 "$DIR"/papermind-*.sql.gz 2>/dev/null | wc -l)"
