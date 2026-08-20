#!/usr/bin/env bash
# Möhləti bitmiş hesabları həqiqətən silir. Cron gündə bir dəfə çağırır:
#
#   30 3 * * * cd ~/papermind && bash scripts/purge-accounts.sh >> ~/purge.log 2>&1
#
# Yedəkdən (03:00) SONRA işləyir — silinən məlumat ən azı bir yedəkdə qalsın
# ki, səhv silmə halında bərpa mümkün olsun.
#
# Sorğu KONTEYNERİN İÇİNDƏN gedir: backend porti internetə açıq deyil
# (yalnız Caddy 80/443 açıqdır), ona görə `localhost:8000`-ə xaricdən
# çatmaq mümkün deyil və olmamalıdır da.

set -uo pipefail
cd "$(dirname "$0")/.."

COMPOSE="docker compose -f docker-compose.prod.yml"
[ -f docker-compose.prod.yml ] || COMPOSE="docker compose"

KEY=$(grep '^ADMIN_API_KEY=' .env 2>/dev/null | tail -1 | cut -d= -f2-)
if [ -z "$KEY" ]; then
  echo "[$(date '+%F %T')] XƏTA: ADMIN_API_KEY .env-də yoxdur"
  exit 1
fi

echo "[$(date '+%F %T')] silinmə möhləti yoxlanılır"
OUT=$($COMPOSE exec -T backend curl -s -X POST \
        -H "X-API-Key: $KEY" \
        http://localhost:8000/api/auth/account/purge 2>&1)

echo "  cavab: $OUT"

# «Çağırış getdi» ilə «silmə oldu» eyni şey deyil — cavabı OXUYURUQ.
case "$OUT" in
  *'"purged"'*) echo "[$(date '+%F %T')] tamamlandı" ;;
  *401*|*Yanlış*) echo "[$(date '+%F %T')] XƏTA: admin açarı qəbul olunmadı"; exit 1 ;;
  *) echo "[$(date '+%F %T')] XƏTA: gözlənilməz cavab"; exit 1 ;;
esac
