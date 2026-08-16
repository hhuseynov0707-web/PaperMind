#!/usr/bin/env bash
# Paddle konfiqurasiyasını .env-ə yazır və backend-i yeniləyir.
#
# Niyə skript, niyə nano deyil: serverə yalnız provayderin web konsolundan
# girmək mümkün olduqda (çıxış SSH portları bloklu), həmin konsolda mətn
# redaktoru işlətmək əziyyətlidir və `|`, dırnaq kimi simvollar korlanır.
# Burada yalnız hərf-rəqəm dəyərləri yazılır, sintaksis skriptin öz üzərindədir.
#
#     cd /root/papermind; bash scripts/set-paddle.sh
#
# Mövcud sətirlər ƏVƏZLƏNİR (silinib yenidən yazılır) — əks halda `.env`-də
# dublikat yaranır və sonuncu qalib gəlir, bu isə səhv dəyərlə işləməyin
# ən asan yoludur. Bir dəfə məhz belə olmuşdu.

set -uo pipefail
cd "$(dirname "$0")/.."

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }

[ -f .env ] || { echo ".env yoxdur"; exit 1; }

cat <<'INTRO'

Paddle konfiqurasiyası
======================
Dəyərləri Paddle panelindən kopyala. Hamısı hərf-rəqəm və alt xəttdir,
xüsusi simvol yoxdur — konsolda problemsiz yazılır.

  PADDLE_CLIENT_TOKEN    Developer Tools -> Authentication -> Client-side tokens
                         (live_... / test_... ilə başlayır, GİZLİ DEYİL)
  PADDLE_WEBHOOK_SECRET  Notifications -> destination -> secret key  (GİZLİDİR)
  PADDLE_PRICE_ID_PRO    Catalog -> Products -> Pro -> Price  (pri_... ilə başlayır)

DİQQƏT: yazdığın dəyərlər ekranda görünür ki, səhvi tuta biləsən.
Bu addımın ekran şəklini paylaşma.

Boş buraxıb Enter basmaq həmin dəyəri DƏYİŞMƏDƏN saxlayır.

INTRO

current() { grep "^$1=" .env | tail -1 | cut -d= -f2-; }

ask() {  # dəyişən adı, izah
  local key="$1" label="$2" cur val
  cur="$(current "$key")"
  if [ -n "$cur" ]; then
    printf '%s (hazırda: %s...%s)\n> ' "$label" "${cur:0:6}" "${cur: -4}"
  else
    printf '%s\n> ' "$label"
  fi
  IFS= read -r val
  [ -z "$val" ] && val="$cur"
  printf '%s' "$val"
}

CLIENT_TOKEN="$(ask PADDLE_CLIENT_TOKEN 'Client-side token')"
WEBHOOK_SECRET="$(ask PADDLE_WEBHOOK_SECRET 'Webhook secret')"
PRICE_ID="$(ask PADDLE_PRICE_ID_PRO 'Pro qiymət ID (pri_...)')"

echo
printf 'Mühit — production üçün Enter, sandbox üçün "s" yaz\n> '
IFS= read -r env_choice
if [ "$env_choice" = "s" ] || [ "$env_choice" = "S" ]; then
  PADDLE_ENV=sandbox
else
  PADDLE_ENV=production
fi

DOMAIN="$(current DOMAIN)"
BASE="https://${DOMAIN}"

echo
echo "Yazılır..."

# Köhnə sətirlər tamamilə silinir, sonra yenidən yazılır — dublikatın qarşısı
# yalnız belə alınır.
KEYS="PAYMENT_PROVIDER PADDLE_CLIENT_TOKEN PADDLE_WEBHOOK_SECRET PADDLE_PRICE_ID_PRO PADDLE_ENVIRONMENT PUBLIC_BASE_URL"
cp .env ".env.backup-$(date +%s)"
TMP="$(mktemp)"
grep -vE "^($(echo $KEYS | tr ' ' '|'))=" .env > "$TMP"
{
  echo ""
  echo "# --- Paddle (scripts/set-paddle.sh tərəfindən yazılıb) ---"
  echo "PAYMENT_PROVIDER=paddle"
  echo "PADDLE_ENVIRONMENT=${PADDLE_ENV}"
  echo "PADDLE_CLIENT_TOKEN=${CLIENT_TOKEN}"
  echo "PADDLE_WEBHOOK_SECRET=${WEBHOOK_SECRET}"
  echo "PADDLE_PRICE_ID_PRO=${PRICE_ID}"
  echo "PUBLIC_BASE_URL=${BASE}"
} >> "$TMP"
mv "$TMP" .env
chmod 600 .env
ok ".env yeniləndi (köhnə nüsxə .env.backup-* kimi saxlanıldı)"

for k in PAYMENT_PROVIDER PADDLE_CLIENT_TOKEN PADDLE_WEBHOOK_SECRET PADDLE_PRICE_ID_PRO; do
  v="$(current "$k")"
  n=$(grep -c "^$k=" .env)
  if [ -z "$v" ]; then
    warn "$k boşdur"
  elif [ "$n" -ne 1 ]; then
    warn "$k $n dəfə yazılıb"
  else
    ok "$k"
  fi
done

echo
echo "Backend yenilənir..."
docker compose -f docker-compose.prod.yml up -d backend >/dev/null 2>&1
sleep 8

echo
echo "Yoxlama:"
# HTTP kodu ilə yoxlamaq İŞLƏMİR: /api/billing/checkout-da `require_user`
# ən əvvəl işləyir, ona görə girişsiz sorğu ödəniş konfiqurasiyasına
# BAXMADAN 401 qaytarır. O 401-i «aktivdir» kimi yozmaq yanlış yaşıl verir —
# bir dəfə məhz belə oldu. Ona görə konteynerin öz mühitinə baxılır.
MISSING=0
for k in PAYMENT_PROVIDER PADDLE_CLIENT_TOKEN PADDLE_WEBHOOK_SECRET PADDLE_PRICE_ID_PRO; do
  v=$(docker compose -f docker-compose.prod.yml exec -T backend printenv "$k" 2>/dev/null | tr -d '\r\n')
  if [ -n "$v" ]; then
    ok "konteynerdə ${k} var"
  else
    warn "konteynerdə ${k} YOXDUR"
    MISSING=$((MISSING+1))
  fi
done

if [ "$MISSING" -eq 0 ]; then
  ok "ödəniş aktivdir"
else
  warn "${MISSING} dəyər konteynerə çatmayıb — konteyner köhnə mühitlə işləyə bilər:"
  echo "      docker compose -f docker-compose.prod.yml up -d --force-recreate backend"
fi

cat <<NEXT

Saytda yenilə və "Pro-ya keç" düyməsini yoxla.
Ekranı təmizləmək üçün:  clear

NEXT
