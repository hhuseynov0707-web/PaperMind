#!/usr/bin/env bash
# Hesab silinəndə məlumatın HƏQİQƏTƏN getdiyini sübut edir.
#
#   bash scripts/verify-deletion.sh
#
# ## Niyə bu ayrıca skriptdir
#
# Kaskad Python məntiqi deyil — xarici açar qaydasıdır (`ON DELETE CASCADE`,
# `SET NULL`). Vahid testlərdəki mock baza onu təqlid edə bilər və test
# keçər, istehsalatda isə məlumat qalar. Yəni belə testin verdiyi əminlik
# saxtadır. Yeganə düzgün sübut real Postgres üzərindədir.
#
# ## İstehsalata toxunurmu
#
# Yalnız SXEMİ oxuyur (`pg_dump --schema-only`, məlumat yoxdur). Sınaq
# birdəfəlik konteynerdə aparılır və konteyner sonunda silinir. İstehsalat
# bazasına heç bir yazma getmir.

set -uo pipefail

HOST="${PM_HOST:-root@2.28.22.89}"
KEY="${PM_KEY:-$HOME/.ssh/papermind}"
DIR="${PM_DIR:-/root/papermind}"
CT="pm-deletion-test"

G='\033[32m'; R='\033[31m'; C='\033[36m'; N='\033[0m'
ok()   { printf "  ${G}OK${N}    %s\n" "$1"; }
bad()  { printf "  ${R}XƏTA${N}  %s\n" "$1"; FAIL=$((FAIL+1)); }
step() { printf "\n${C}==> %s${N}\n" "$1"; }
FAIL=0
SSH="ssh -o ConnectTimeout=20 -i $KEY $HOST"

cleanup() { $SSH "docker rm -f $CT >/dev/null 2>&1" >/dev/null 2>&1 || true; }
trap cleanup EXIT

step "1/4 · Sxem götürülür (yalnız oxuma, məlumat yox)"
$SSH "cd $DIR && docker compose -f docker-compose.prod.yml exec -T postgres \
      pg_dump -U elmradari --schema-only elmradari > /tmp/schema.sql && wc -l < /tmp/schema.sql" \
  | tr -d '\r' | sed 's/^/  sxem sətri: /' || { bad "sxem alınmadı"; exit 1; }

step "2/4 · Birdəfəlik Postgres"
$SSH "docker rm -f $CT >/dev/null 2>&1
      docker run -d --name $CT -e POSTGRES_PASSWORD=t -e POSTGRES_USER=elmradari \
        -e POSTGRES_DB=elmradari pgvector/pgvector:pg16 >/dev/null" || { bad "qalxmadı"; exit 1; }
for i in $(seq 1 30); do
  $SSH "docker exec $CT pg_isready -U elmradari" >/dev/null 2>&1 && break
  [ "$i" = 30 ] && { bad "hazır olmadı"; exit 1; }
done
$SSH "docker exec -i $CT psql -U elmradari -d elmradari -q < /tmp/schema.sql" >/dev/null 2>&1
ok "sxem yükləndi"

step "3/4 · Sınaq istifadəçisi və ona bağlı sətirlər"
SQL_ERR=$($SSH "docker exec -i $CT psql -U elmradari -d elmradari -q" <<'SQL' 2>&1
-- `email_verified` NOT NULL-dur və server tərəfli standartı YOXDUR
-- (standart yalnız SQLAlchemy modelindədir), ona görə açıq verilir.
INSERT INTO users (id, email, password_hash, plan, is_active, credits_used, email_verified)
VALUES (99001, 'silinecek@test.invalid', 'x', 'free', true, 0, false);
INSERT INTO user_sessions (user_id, token_hash, expires_at)
VALUES (99001, 'hash1', now() + interval '1 day');
INSERT INTO papers (id, title, abstract, source, language) VALUES (99001, 'T', 'A', 'test', 'en');
INSERT INTO saved_papers (user_id, paper_id, saved) VALUES (99001, 99001, true);
INSERT INTO documents (id, user_id, filename, title, digest, status, pages, chars, chunk_count)
VALUES (99001, 99001, 'f.pdf', 'T', 'd1', 'ready', 1, 100, 1);
INSERT INTO document_chunks (document_id, page, chunk_index, content)
VALUES (99001, 1, 0, 'mətn');
INSERT INTO usage_events (user_id, action, credits) VALUES (99001, 'ask', 1);
INSERT INTO billing_events (event_id, event_type, user_id, payload)
VALUES ('evt_test_99001', 'subscription.created', 99001, '{}'::jsonb);
SQL
)
# Hazırlıq düşərsə skript DAYANIR. Əvvəlki variant xətanı /dev/null-a atırdı
# və sonra «hər şey silinib» kimi yanlış nəticə çıxarırdı — halbuki heç nə
# yaradılmamışdı. Boş bazada silmə testi həmişə «keçir».
if echo "$SQL_ERR" | grep -qi "^ERROR"; then
  bad "sınaq sətirləri yaradılmadı:"
  echo "$SQL_ERR" | grep -i "^ERROR" | head -3 | sed 's/^/      /'
  exit 1
fi
BEFORE=$($SSH "docker exec $CT psql -U elmradari -d elmradari -tAc \
  \"SELECT (SELECT count(*) FROM user_sessions WHERE user_id=99001)||' '||
           (SELECT count(*) FROM saved_papers WHERE user_id=99001)||' '||
           (SELECT count(*) FROM documents WHERE user_id=99001)||' '||
           (SELECT count(*) FROM document_chunks WHERE document_id=99001)||' '||
           (SELECT count(*) FROM usage_events WHERE user_id=99001)||' '||
           (SELECT count(*) FROM billing_events WHERE event_id='evt_test_99001')\"" \
  2>/dev/null | tr -d '\r')
echo "  əvvəl (sessiya/kitabxana/sənəd/parça/istifadə/ödəniş): $BEFORE"
[ "$BEFORE" = "1 1 1 1 1 1" ] && ok "sətirlər yaradıldı" || bad "hazırlıq alınmadı: $BEFORE"

step "4/4 · İstifadəçi silinir — nə qalır?"
$SSH "docker exec $CT psql -U elmradari -d elmradari -qc 'DELETE FROM users WHERE id=99001'" >/dev/null 2>&1

AFTER=$($SSH "docker exec $CT psql -U elmradari -d elmradari -tAc \
  \"SELECT (SELECT count(*) FROM user_sessions WHERE user_id=99001)||' '||
           (SELECT count(*) FROM saved_papers WHERE user_id=99001)||' '||
           (SELECT count(*) FROM documents WHERE user_id=99001)||' '||
           (SELECT count(*) FROM document_chunks WHERE document_id=99001)||' '||
           (SELECT count(*) FROM usage_events WHERE user_id=99001)||' '||
           (SELECT count(*) FROM billing_events WHERE event_id='evt_test_99001')\"" \
  2>/dev/null | tr -d '\r')
echo "  sonra (sessiya/kitabxana/sənəd/parça/istifadə/ödəniş): $AFTER"

# Şəxsi məlumat GETMƏLİ, maliyyə qeydi QALMALIDIR.
if [ "$AFTER" = "0 0 0 0 0 1" ]; then
  ok "şəxsi məlumat tam silindi, ödəniş qeydi qaldı"
else
  bad "gözlənilən '0 0 0 0 0 1', alınan '$AFTER'"
fi

ORPHAN=$($SSH "docker exec $CT psql -U elmradari -d elmradari -tAc \
  \"SELECT coalesce(user_id::text,'NULL') FROM billing_events WHERE event_id='evt_test_99001'\"" \
  2>/dev/null | tr -d '\r')
if [ "$ORPHAN" = "NULL" ]; then
  ok "ödəniş qeydinin istifadəçi bağlantısı qırıldı (user_id = NULL)"
else
  bad "billing_events.user_id hələ də doludur: $ORPHAN"
fi

echo
echo "======================================"
[ "$FAIL" -eq 0 ] && printf "Nəticə: ${G}silmə düzgün işləyir${N}\n" \
                  || printf "Nəticə: ${R}%s xəta${N}\n" "$FAIL"
exit "$FAIL"
