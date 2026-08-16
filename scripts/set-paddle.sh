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

# Token/ID üçün cari dəyər — KORLANMIŞDIRSA boş sayılır.
# Səbəb: korlanmış dəyər «hazırda: ...» kimi təklif olunsa, istifadəçi Enter
# basıb zibili saxlayır və nasazlıq təkrarlanır. Etibarlı Paddle dəyəri
# yalnız hərf, rəqəm, alt xətt və defis saxlayır.
valid_token() {
  case "$1" in
    ''|*[!A-Za-z0-9_-]*) return 1 ;;
    *) return 0 ;;
  esac
}

current_token() {
  local v; v="$(current "$1")"
  valid_token "$v" || v=""

  # `.env`-də etibarlı dəyər yoxdursa, EHTİYAT NÜSXƏLƏRƏ bax — ən yenidən
  # köhnəyə doğru. Səbəb: dəyəri bu skriptin öz səhvi silib və istifadəçini
  # onu Paddle panelindən yenidən tapmağa məcbur etmək düzgün deyil.
  if [ -z "$v" ]; then
    local f c
    for f in $(ls -1t .env.backup-* 2>/dev/null); do
      c="$(grep "^$1=" "$f" | tail -1 | cut -d= -f2- | tr -d '[:space:]')"
      if valid_token "$c"; then v="$c"; break; fi
    done
    [ -n "$v" ] && printf '  (nüsxədən bərpa olundu)\n' >&2
  fi
  printf '%s' "$v"
}

ask() {  # dəyişən adı, izah
  # Sual mətni STDERR-ə gedir. stdout-a yazsaq, `$(...)` onu da tutur və
  # prompt DƏYƏRİN İÇİNƏ düşür — bir dəfə məhz belə oldu və `.env`-ə
  # «> live_...» sətri yazılıb faylı oxunmaz etdi.
  local key="$1" label="$2" cur val
  cur="$(current_token "$key")"
  # BOŞ DƏYƏR YAZILMIR — sual təkrarlanır. Əvvəl belə deyildi: korlanmış cari
  # dəyər «boş» sayılırdı, istifadəçi Enter basırdı və skript sakitcə BOŞ
  # dəyər yazırdı. Nəticədə ödəniş işləmirdi, `.env` isə dolu görünürdü.
  while : ; do
    if [ -n "$cur" ]; then
      printf '%s (hazırda: %s...%s — saxlamaq üçün Enter)\n> ' \
        "$label" "${cur:0:6}" "${cur: -4}" >&2
    else
      printf '%s\n> ' "$label" >&2
    fi
    IFS= read -r val
    [ -z "$val" ] && val="$cur"
    # Kənar boşluqlar kəsilir: kopyalayanda sona boşluq düşməsi adi haldır və
    # `.env`-də görünməz səhvə çevrilir.
    val="$(printf '%s' "$val" | tr -d '[:space:]')"
    [ -n "$val" ] && break
    printf 'Dəyər boş ola bilməz — Paddle panelindən kopyala.\n\n' >&2
  done
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
# Dəyərlərin formasını yoxla. Səhv dəyər qəbul edilsə, nasazlıq yalnız
# checkout anında üzə çıxır və səbəbi görünmür.
for pair in "CLIENT_TOKEN:$CLIENT_TOKEN:live_,test_" "PRICE_ID:$PRICE_ID:pri_"; do
  name="${pair%%:*}"; rest="${pair#*:}"; val="${rest%%:*}"; prefixes="${rest#*:}"
  matched=no
  IFS=, read -r -a plist <<< "$prefixes"
  for p in "${plist[@]}"; do
    case "$val" in "$p"*) matched=yes ;; esac
  done
  [ "$matched" = yes ] || warn "$name gözlənilən prefikslə başlamır ($prefixes) — dəyəri yoxla: ${val:0:10}..."
done

echo "Yazılır..."

# Köhnə sətirlər tamamilə silinir, sonra yenidən yazılır — dublikatın qarşısı
# yalnız belə alınır.
KEYS="PAYMENT_PROVIDER PADDLE_CLIENT_TOKEN PADDLE_WEBHOOK_SECRET PADDLE_PRICE_ID_PRO PADDLE_ENVIRONMENT PUBLIC_BASE_URL"
cp .env ".env.backup-$(date +%s)"
TMP="$(mktemp)"
grep -vE "^($(echo $KEYS | tr ' ' '|'))=" .env > "$TMP"

# Korlanmış sətirləri təmizlə. Etibarlı `.env` sətri ya boşdur, ya şərhdir,
# ya da AD=dəyər formasındadır. Başqa hər şey Docker-in faylı oxumasını
# tamamilə dayandırır: «unexpected character in variable name».
JUNK=$(grep -cvE '^[[:space:]]*($|#|[A-Za-z_][A-Za-z0-9_]*=)' "$TMP")
if [ "$JUNK" -gt 0 ]; then
  grep -E '^[[:space:]]*($|#|[A-Za-z_][A-Za-z0-9_]*=)' "$TMP" > "${TMP}.clean"
  mv "${TMP}.clean" "$TMP"
  warn "${JUNK} korlanmış sətir silindi"
fi
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
