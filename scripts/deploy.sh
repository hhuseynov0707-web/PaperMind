#!/usr/bin/env bash
# Produksiya deploy-u — bir əmrlə.
#
# Niyə skript: bəzi şəbəkələr çıxış SSH portlarını bloklayır və serverə yalnız
# provayderin web konsolundan girmək mümkün olur. O konsolda `|`, dırnaq və
# bir sıra simvollar korlanır, yəni uzun əmr yazmaq praktiki deyil. Bu fayl
# həmin problemi tamamilə aradan qaldırır:
#
#     cd /root/papermind; git pull; bash scripts/deploy.sh
#
# Yuxarıdakı sətirdə korlanan simvol yoxdur.
#
# İdempotentdir — təkrar işlətmək təhlükəsizdir.

set -uo pipefail
cd "$(dirname "$0")/.."

C="docker compose -f docker-compose.prod.yml"
PASS=0; FAIL=0

info() { printf '\n\033[36m==> %s\033[0m\n' "$1"; }
ok()   { printf '  \033[32mOK\033[0m    %s\n' "$1"; PASS=$((PASS+1)); }
bad()  { printf '  \033[31mXƏTA\033[0m  %s\n' "$1"; FAIL=$((FAIL+1)); }
warn() { printf '  \033[33mDİQQƏT\033[0m %s\n' "$1"; }

# ---------------------------------------------------------------- 1. .env

info "1/5 · Konfiqurasiya"

if [ ! -f .env ]; then
  bad ".env yoxdur"
  exit 1
fi

# Dəyərlər EKRANA ÇIXARILMIR — yalnız var/yox və neçə dəfə. Konsol görüntüsü
# ekran şəkli kimi paylaşıla bilər, sirrlər isə orada görünməməlidir.
# MƏCBURİ: kodda defolt dəyəri yoxdur və ya defolt təhlükəlidir.
for k in GROQ_API_KEY ADMIN_API_KEY POSTGRES_PASSWORD DOMAIN; do
  n=$(grep -c "^${k}=" .env)
  v=$(grep "^${k}=" .env | tail -1 | cut -d= -f2-)
  if [ -z "$v" ]; then
    bad "${k} boşdur"
  elif [ "$n" -gt 1 ]; then
    warn "${k} ${n} dəfə yazılıb — sonuncu qalib gəlir, təmizlə"
  else
    ok "${k}"
  fi
done

# İSTƏYƏ GÖRƏ: config.py-da düzgün defoltları var (public_browse=true,
# session_cookie_secure=true, pro_monthly_credits=700). Yazılmayıbsa deploy
# DAYANMIR — sadəcə hansı dəyərin işlədiləcəyi bildirilir.
for k in PUBLIC_BROWSE SESSION_COOKIE_SECURE PRO_MONTHLY_CREDITS PUBLIC_BASE_URL; do
  v=$(grep "^${k}=" .env | tail -1 | cut -d= -f2-)
  [ -n "$v" ] && ok "${k}=${v}" || warn "${k} yoxdur — koddakı defolt işlənəcək"
done

# Ödəniş İSTƏYƏ GÖRƏdir: qurulmayıbsa tətbiq tam işləyir, yalnız billing
# endpoint-ləri 503 verir. Ona görə burada xəta yox, xəbərdarlıq.
PAY=$(grep "^PAYMENT_PROVIDER=" .env | tail -1 | cut -d= -f2-)
if [ -n "$PAY" ]; then
  for k in PADDLE_CLIENT_TOKEN PADDLE_WEBHOOK_SECRET PADDLE_PRICE_ID_PRO; do
    v=$(grep "^${k}=" .env | tail -1 | cut -d= -f2-)
    [ -n "$v" ] && ok "${k}" || bad "${k} boşdur (PAYMENT_PROVIDER=${PAY} təyin olunub)"
  done
else
  warn "PAYMENT_PROVIDER boşdur — abunə sönülüdür, qalan hər şey işləyir"
fi

# Model adları provayderdə dəyişir və silinir. Bunu build-dən ƏVVƏL tutmaq
# lazımdır: əks halda 5 dəqiqə build gözləyib sonra hər LLM çağırışının
# 404 aldığını görürsən — özü də yalnız loga baxsan.
echo
if ! bash scripts/check-models.sh; then
  FAIL=$((FAIL+1))
fi

[ "$FAIL" -gt 0 ] && { echo; echo "Xətaları düzəlt, sonra təkrar işlət."; exit 1; }

# ------------------------------------------------------------- 2. qaldırma

info "2/5 · Build və qaldırma"
echo "  (ilk dəfə 3-5 dəqiqə çəkir — yeni asılılıqlar quraşdırılır)"
if ! $C up -d --build backend; then
  bad "build uğursuz oldu"
  exit 1
fi
ok "backend qaldırıldı"

# --------------------------------------------------------------- 3. sağlamlıq

info "3/5 · Backend hazırlanır"
HEALTHY=no
for i in $(seq 1 40); do
  code=$($C exec -T backend curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null)
  if [ "$code" = "200" ]; then HEALTHY=yes; break; fi
  sleep 5
done
if [ "$HEALTHY" = yes ]; then
  ok "backend cavab verir"
else
  bad "backend 200 saniyə ərzində qalxmadı"
  echo
  echo "Son loglar:"
  $C logs --tail 40 backend
  exit 1
fi

# Modelin adı düzgün olsa da cavab verməyə bilər (kvota, rejim dəyişikliyi,
# provayder nasazlığı). Ona görə burada REAL çağırış edilir — 401 ölçmək
# qorumanı ölçməkdir, işlədiyini yox. Bu, ödənişli məhsulun nüvə funksiyasıdır.
info "3.5/5 · LLM cavab verirmi"
SMOKE=$($C exec -T backend python -c "
from app.providers import get_llm
try:
    # max_tokens bol verilir: gpt-oss ailəsi düşüncə kanalı işlədir və dar
    # limitdə bütün büdcəni ora xərcləyib BOŞ məzmun qaytarır.
    out = get_llm().complete('Cavabı bir sözlə ver.', 'De: OK', max_tokens=64)
    out = (out or '').strip()
    print(('CAVAB:' + out[:40]) if out else 'BOS:')
except Exception as e:
    print('XETA:' + str(e)[:160])
" 2>/dev/null | tr -d '
')

case "$SMOKE" in
  CAVAB:*) ok "LLM cavab verdi (${SMOKE#CAVAB:})" ;;
  # BOŞ cavab uğur DEYİL. Əvvəl belə deyildi: yoxlama yalnız istisna
  # atılmadığına baxırdı və model heç nə qaytarmayanda da «OK» verirdi.
  BOS:*)   bad "LLM boş cavab qaytardı — model məzmun istehsal etmir" ;;
  XETA:*)  bad "LLM cavab vermir — ${SMOKE#XETA:}" ;;
  *)       bad "LLM sınağı nəticəsiz qaldı: ${SMOKE:-bos}" ;;
esac

# ------------------------------------------------------------- 4. cədvəllər

info "4/5 · Baza"
TBL=$($C exec -T postgres psql -U elmradari -d elmradari -tAc \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('users','user_sessions','saved_papers','usage_events','billing_events')" 2>/dev/null | tr -d '[:space:]')
if [ "$TBL" = "5" ]; then
  ok "hesab cədvəlləri yaradılıb (5/5)"
else
  bad "hesab cədvəlləri natamam (${TBL:-0}/5)"
fi

PAPERS=$($C exec -T postgres psql -U elmradari -d elmradari -tAc \
  "SELECT count(*) FROM papers" 2>/dev/null | tr -d '[:space:]')
ok "korpus: ${PAPERS:-?} məqalə"

# --------------------------------------------------------------- 5. canlı

info "5/5 · Canlı yoxlama"
DOMAIN=$(grep "^DOMAIN=" .env | tail -1 | cut -d= -f2-)
BASE="https://${DOMAIN}"

check() {  # ad, gözlənilən kod, curl arqumentləri...
  local name="$1" want="$2"; shift 2
  local got
  got=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 "$@")
  if [ "$got" = "$want" ]; then ok "${name} (${got})"; else bad "${name}: ${got} gəldi, ${want} gözlənilirdi"; fi
}

check "sayt açılır"            200 "$BASE/"
check "axtarış hesabsız işləyir" 200 "$BASE/api/search?q=transformer"
check "sual hesab tələb edir"  401 -X POST "$BASE/api/ask" \
      -H "Content-Type: application/json" -d '{"question":"test"}'
check "yazma açar tələb edir"  401 -X POST "$BASE/api/ingest" \
      -H "Content-Type: application/json" -d '{"papers":[]}'
check "plan siyahısı açıqdır"  200 "$BASE/api/auth/plans"

echo
echo "======================================"
printf 'Nəticə: \033[32m%d OK\033[0m · \033[31m%d xəta\033[0m\n' "$PASS" "$FAIL"
if [ "$FAIL" -eq 0 ]; then
  echo
  echo "Deploy tamamlandı. İndi ${BASE} saytına gir və hesab yarat."
else
  echo
  echo "Xətalar var — yuxarıdakı sətirlərə bax."
  exit 1
fi
