#!/usr/bin/env bash
# Hesaba ƏL İLƏ plan verir — ödənişdən yan keçərək. SERVERDƏ işlədilir:
#
#   cd ~/papermind && bash scripts/grant-plan.sh test@example.com pro
#   cd ~/papermind && bash scripts/grant-plan.sh test@example.com free
#
# ## Nə üçündür
#
# Sınaq və dəstək halları: öz hesabında Pro-nu yoxlamaq, ödənişi düşmüş
# istifadəçiyə müvəqqəti giriş vermək.
#
# ## `subscription_status` QƏSDƏN toxunulmur
#
# Onu «active» etmək cazibədar görünür, amma iki şeyi sındırır:
#   1. Hesab silmə axını aktiv abunəliyi bloklayır — yəni bu hesabı sonra
#      silmək mümkün olmazdı.
#   2. Hesab panelində abunəlik idarəetməsi görünər, Paddle-da isə belə
#      abunəlik yoxdur — keçid heç yerə aparmaz.
# Əl ilə verilmiş plan abunəlik DEYİL; sahə boş qalmalıdır ki, sistem
# ikisini qarışdırmasın.
#
# ## Kredit
#
# `credits_left` planın limitindən CARİ dövrdə işlənəni çıxır. Pulsuz planda
# xərclənmiş kreditlər Pro-ya keçəndə də sayılır, ona görə sayğac sıfırlanır —
# yeni plan təmiz başlamalıdır.

set -uo pipefail
cd "$(dirname "$0")/.."

EMAIL="${1:-}"
PLAN="${2:-pro}"

if [ -z "$EMAIL" ]; then
  echo "İstifadə:  bash scripts/grant-plan.sh <e-poçt> [pro|free]"
  exit 1
fi
case "$PLAN" in
  pro|free) ;;
  *) echo "Plan yalnız 'pro' və ya 'free' ola bilər (verilən: $PLAN)"; exit 1 ;;
esac

EMAIL="$(printf '%s' "$EMAIL" | tr -d '[:space:]' | tr 'A-Z' 'a-z')"

COMPOSE="docker compose -f docker-compose.prod.yml"
[ -f docker-compose.prod.yml ] || COMPOSE="docker compose"
set -a; [ -f .env ] && . ./.env; set +a
DBU="${POSTGRES_USER:-elmradari}"; DBN="${POSTGRES_DB:-elmradari}"

q() { $COMPOSE exec -T postgres psql -U "$DBU" -d "$DBN" -tAc "$1" 2>/dev/null | tr -d '\r'; }

# E-poçt SQL-ə birbaşa yapışdırılmır — dollar-işarəli sabit blok içindədir,
# yəni dırnaq və apostrof sorğunu poza bilmir.
ESC="\$pm\$${EMAIL}\$pm\$"

BEFORE=$(q "SELECT plan || ' | kredit işlənib: ' || coalesce(credits_used,0) || ' | dövr: ' || coalesce(credits_period,'-') || ' | abunəlik: ' || coalesce(subscription_status,'yoxdur') FROM users WHERE email = $ESC")

if [ -z "$BEFORE" ]; then
  echo "  Belə hesab yoxdur: $EMAIL"
  echo
  echo "  Mövcud hesablar:"
  q "SELECT '    ' || email || '  (' || plan || ')' FROM users ORDER BY created_at"
  exit 1
fi

echo "  hesab:  $EMAIL"
echo "  əvvəl:  $BEFORE"

# `credits_period` NULL edilir ki, növbəti yazılışda dövr yenidən qurulsun
# və köhnə sayğac nəzərə alınmasın.
q "UPDATE users SET plan = '$PLAN', credits_used = 0, credits_period = NULL WHERE email = $ESC" >/dev/null

AFTER=$(q "SELECT plan || ' | kredit işlənib: ' || coalesce(credits_used,0) || ' | abunəlik: ' || coalesce(subscription_status,'yoxdur') FROM users WHERE email = $ESC")
echo "  sonra:  $AFTER"

# «UPDATE getdi» ilə «plan dəyişdi» eyni şey deyil — nəticəni OXUYURUQ.
case "$AFTER" in
  "$PLAN "*) echo; echo "  OK — plan '$PLAN' oldu." ;;
  *) echo; echo "  XƏTA — plan dəyişmədi."; exit 1 ;;
esac

echo
echo "  Qeyd: bu, ödənişdən yan keçən ƏL İLƏ verilmiş plandır."
echo "  Paddle-da abunəlik yaranmır və heç nə çəkilmir."
echo "  Geri almaq üçün:  bash scripts/grant-plan.sh $EMAIL free"
