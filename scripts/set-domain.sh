#!/usr/bin/env bash
# Yeni domenə keçid. SERVERDƏ işlədilir:
#
#   cd ~/papermind && bash scripts/set-domain.sh papermind.io
#
# ## Köhnə domen İŞLƏMƏYƏ DAVAM EDİR
#
# Caddy hər ikisinə sertifikat alır və hər ikisinə cavab verir. Səbəb:
# keçid anında paylaşılmış keçidlər, Paddle-dakı qeyd və brauzer əlfəcinləri
# hələ köhnə ünvana baxır. Birdən kəsmək o keçidlərin hamısını sındırardı.
# Hər şey oturandan sonra köhnəni `.env`-dən çıxarmaq olar.
#
# ## Ən vacib yoxlama
#
# DNS-in «cavab verməsi» kifayət deyil — BİZİM serverə baxdığını yoxlayırıq.
# Başqa ünvana baxan domen üçün Let's Encrypt sertifikat verə bilmir və
# Caddy sonsuz cəhd döngüsünə düşür; bunu əvvəlcədən tutmaq lazımdır.

set -uo pipefail
cd "$(dirname "$0")/.."

G='\033[32m'; R='\033[31m'; Y='\033[33m'; C='\033[36m'; N='\033[0m'
ok()   { printf "  ${G}OK${N}    %s\n" "$1"; }
bad()  { printf "  ${R}XƏTA${N}  %s\n" "$1"; }
warn() { printf "  ${Y}DİQQƏT${N} %s\n" "$1"; }
step() { printf "\n${C}==> %s${N}\n" "$1"; }

NEW="${1:-}"
if [ -z "$NEW" ]; then
  echo "İstifadə:  bash scripts/set-domain.sh yenidomen.com"
  exit 1
fi
NEW="$(printf '%s' "$NEW" | tr -d '[:space:]' | sed 's#^https\?://##; s#/.*##' | tr 'A-Z' 'a-z')"

COMPOSE="docker compose -f docker-compose.prod.yml"
[ -f docker-compose.prod.yml ] || COMPOSE="docker compose"

step "1/5 · DNS yoxlanışı"
MY_IP=$(curl -s --max-time 15 https://api.ipify.org || hostname -I | awk '{print $1}')
echo "  bu serverin IP-si: $MY_IP"

RESOLVED=$(getent ahostsv4 "$NEW" 2>/dev/null | awk '{print $1}' | sort -u | head -3)
if [ -z "$RESOLVED" ]; then
  bad "$NEW həll olunmur — A qeydi hələ yayılmayıb"
  echo "      Registrarda A qeydi yarat:  @  ->  $MY_IP"
  echo "      Yayılma 5 dəqiqədən bir neçə saata qədər çəkə bilər."
  exit 1
fi
echo "  $NEW -> $(echo "$RESOLVED" | tr '\n' ' ')"

# «Həll olunur» ilə «bizə baxır» eyni şey deyil. Bu fərqi yoxlamamaq
# bu layihədə artıq bir dəfə yalançı «hazırdır» nəticəsi verib.
if ! echo "$RESOLVED" | grep -qx "$MY_IP"; then
  bad "$NEW BAŞQA ünvana baxır — sertifikat alınmayacaq"
  echo "      A qeydini $MY_IP-ə yönəlt və yayılmanı gözlə."
  exit 1
fi
ok "DNS bu serverə baxır"

step "2/5 · .env yenilənir"
OLD=$(grep '^DOMAIN=' .env | tail -1 | cut -d= -f2-)
echo "  köhnə: $OLD"

case "$OLD" in
  *"$NEW"*) BOTH="$OLD" ;;                 # onsuz da içindədir
  "")       BOTH="$NEW" ;;
  *)        BOTH="$NEW, $OLD" ;;           # yeni ƏVVƏLDƏ — kanonik odur
esac

cp .env ".env.backup-$(date +%F-%H%M)"
sed -i "s#^DOMAIN=.*#DOMAIN=$BOTH#" .env
sed -i "s#^PUBLIC_BASE_URL=.*#PUBLIC_BASE_URL=https://$NEW#" .env
ok "DOMAIN=$BOTH"
ok "PUBLIC_BASE_URL=https://$NEW"

step "3/5 · Caddy yenidən qurulur"
# Tək fayl mount olunduğu üçün `reload` kifayət etmir — konteyner yenidən
# yaradılır (bax deploy.sh-dəki eyni izah).
$COMPOSE up -d --force-recreate caddy >/dev/null 2>&1 && ok "qaldırıldı" || { bad "qalxmadı"; exit 1; }

step "4/5 · Sertifikat gözlənilir"
# Let's Encrypt bir neçə saniyə çəkir. Nəticəni ÖLÇÜRÜK, gözləyib
# «yəqin oldu» demirik.
GOT=no
for i in $(seq 1 30); do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "https://$NEW/health" 2>/dev/null)
  if [ "$CODE" = "200" ]; then GOT=yes; break; fi
  sleep 4
done
if [ "$GOT" = yes ]; then
  ok "https://$NEW cavab verir (200)"
else
  bad "sertifikat alınmadı — Caddy loglarına bax:"
  echo "      $COMPOSE logs --tail 40 caddy"
  exit 1
fi

step "5/5 · Köhnə domen hələ işləyirmi"
for d in $(echo "$BOTH" | tr ',' ' '); do
  d=$(printf '%s' "$d" | tr -d '[:space:]')
  CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 12 "https://$d/health" 2>/dev/null)
  [ "$CODE" = "200" ] && ok "$d -> 200" || warn "$d -> $CODE"
done

echo
echo "======================================"
printf "${G}Hazırdır${N} — kanonik ünvan: https://%s\n" "$NEW"
echo
echo "Növbəti addımlar (ƏL İLƏ):"
echo "  1. Paddle -> Checkout -> Website approval -> yeni domeni əlavə et"
echo "  2. Backend-i yenidən qaldır ki, PUBLIC_BASE_URL tətbiq olunsun:"
echo "       $COMPOSE up -d --force-recreate backend"
echo "  3. Hər şey oturandan sonra köhnə domeni .env-dəki DOMAIN-dən çıxar"
