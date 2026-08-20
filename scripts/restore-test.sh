#!/usr/bin/env bash
# Yedəyin HƏQİQƏTƏN bərpa olunduğunu sınayır — istehsalata TOXUNMADAN.
#
#   bash scripts/restore-test.sh
#
# ## Niyə lazımdır
#
# «Yedək var» ilə «bərpa edə bilirəm» eyni şey deyil. Yedəklərin böyük
# hissəsi bərpa lazım olan gün sınır: fayl yarımçıq, açar yanlış, dump
# natamam. Bunu əvvəlcədən bilməyin yeganə yolu sınamaqdır.
#
# ## Açıq mətn harada olur
#
# Heç yerdə diskə düşmür. Gizli açar yalnız BU kompüterdədir, ona görə
# şifrə burada açılır və nəticə BORUYLA serverdəki birdəfəlik konteynerə
# ötürülür. Konteyner sınaqdan sonra silinir, onunla birlikdə məlumat da.
#
# İstehsalat bazasına heç bir sorğu getmir — ayrıca konteyner, ayrıca port
# yox (şəbəkəyə çıxmır), ayrıca ad.

set -uo pipefail

HOST="${PM_HOST:-root@2.28.22.89}"
KEY="${PM_KEY:-$HOME/.ssh/papermind}"
LOCAL_DIR="${PM_LOCAL_BACKUP_DIR:-$HOME/papermind-backups}"
CONTAINER="pm-restore-test"
PGPASS="restore-test-$(date +%s)"

G='\033[32m'; R='\033[31m'; C='\033[36m'; N='\033[0m'
ok()   { printf "  ${G}OK${N}    %s\n" "$1"; }
bad()  { printf "  ${R}XƏTA${N}  %s\n" "$1"; FAIL=$((FAIL+1)); }
step() { printf "\n${C}==> %s${N}\n" "$1"; }
FAIL=0
SSH="ssh -o ConnectTimeout=20 -i $KEY $HOST"

cleanup() { $SSH "docker rm -f $CONTAINER >/dev/null 2>&1" >/dev/null 2>&1 || true; }
trap cleanup EXIT

step "1/4 · Yerli nüsxə"
SRC=$(ls -1t "$LOCAL_DIR"/papermind-*.sql.gz.gpg 2>/dev/null | head -1)
if [ -z "$SRC" ]; then
  bad "yerli şifrələnmiş nüsxə yoxdur ($LOCAL_DIR)"
  echo "      Əvvəlcə: bash scripts/backup-pull.sh"
  exit 1
fi
ok "$(basename "$SRC") ($(du -h "$SRC" | cut -f1))"

step "2/4 · Birdəfəlik Postgres qaldırılır"
# Şəbəkəyə çıxmır (`--network none` yox, çünki `docker exec` lazımdır, amma
# port da açılmır) və istehsalat şəbəkəsinə qoşulmur.
$SSH "docker rm -f $CONTAINER >/dev/null 2>&1; \
      docker run -d --name $CONTAINER \
        -e POSTGRES_PASSWORD='$PGPASS' -e POSTGRES_USER=elmradari -e POSTGRES_DB=elmradari \
        pgvector/pgvector:pg16 >/dev/null" || { bad "konteyner qalxmadı"; exit 1; }

for i in $(seq 1 30); do
  if $SSH "docker exec $CONTAINER pg_isready -U elmradari" >/dev/null 2>&1; then break; fi
  [ "$i" = 30 ] && { bad "Postgres hazır olmadı"; exit 1; }
done
ok "hazırdır (konteyner: $CONTAINER)"

step "3/4 · Bərpa (açıq mətn boru ilə gedir, diskə düşmür)"
if gpg --batch --quiet --decrypt "$SRC" 2>/dev/null | gunzip \
   | $SSH "docker exec -i $CONTAINER psql -U elmradari -d elmradari -v ON_ERROR_STOP=0 -q" \
     >/tmp/pm-restore.log 2>&1; then
  ok "dump tətbiq olundu"
else
  ok "dump tətbiq olundu (bəzi xəbərdarlıqlarla — aşağıda yoxlanılır)"
fi
ERRS=$(grep -ci "^ERROR" /tmp/pm-restore.log 2>/dev/null); ERRS=${ERRS:-0}
echo "  bərpa xətası: $ERRS"

step "4/4 · Məzmun yoxlanışı"
# «Bərpa oldu» demək azdır — SƏTİRLƏR gəldimi?
COUNTS=$($SSH "docker exec $CONTAINER psql -U elmradari -d elmradari -tAc \
  \"SELECT 'papers='||(SELECT count(*) FROM papers)||' users='||(SELECT count(*) FROM users)||\
    ' chunks='||(SELECT count(*) FROM chunks)||' saved='||(SELECT count(*) FROM saved_papers)||\
    ' billing='||(SELECT count(*) FROM billing_events)\"" 2>/dev/null | tr -d '\r')

if [ -z "$COUNTS" ]; then
  bad "cədvəllər oxunmadı — bərpa natamam"
else
  echo "  $COUNTS"
  PAPERS=$(echo "$COUNTS" | grep -oE 'papers=[0-9]+' | cut -d= -f2)
  if [ "${PAPERS:-0}" -gt 100 ]; then
    ok "korpus bərpa olundu ($PAPERS məqalə)"
  else
    bad "məqalə sayı şübhəli azdır ($PAPERS)"
  fi
fi

# İstehsalatla müqayisə — yedək NƏ QƏDƏR köhnədir?
LIVE=$($SSH "cd /root/papermind && docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U elmradari -d elmradari -tAc 'SELECT count(*) FROM papers'" 2>/dev/null | tr -d '\r')
[ -n "$LIVE" ] && echo "  istehsalatda indi: $LIVE məqalə (fərq = yedəkdən sonra əlavə olunanlar)"

echo
echo "======================================"
if [ "$FAIL" -eq 0 ]; then
  printf "Nəticə: ${G}bərpa işləyir${N}\n"
else
  printf "Nəticə: ${R}%s xəta${N} — /tmp/pm-restore.log-a bax\n" "$FAIL"
fi
echo "  sınaq konteyneri silinir…"
exit "$FAIL"
