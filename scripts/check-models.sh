#!/usr/bin/env bash
# Konfiqurasiyadakı LLM modellərinin provayderdə HƏQİQƏTƏN mövcud olduğunu
# yoxlayır.
#
# Niyə lazımdır: provayderlər model adlarını silir və dəyişir. Bizdə tam bu
# baş verdi — `llama-3.1-8b-instant` və `llama-3.3-70b-versatile` bir gün
# yoxa çıxdı. Nəticə səssiz idi: çıxarış skripti 3 105 məqaləni emal
# «etdi», hər birində 404 aldı və sıfır nəticə ilə bitəcəkdi; sual-cavab isə
# istifadəçi üçün sadəcə xəta verirdi.
#
# Deploy bunu tutmurdu, çünki yalnız endpoint-in 401 qaytardığına baxırdı —
# yəni qorumanı ölçürdü, İŞLƏYİB-İŞLƏMƏDİYİNİ yox.
#
#     bash scripts/check-models.sh

set -uo pipefail
cd "$(dirname "$0")/.."

ok()   { printf '  \033[32mOK\033[0m    %s\n' "$1"; }
bad()  { printf '  \033[31mXƏTA\033[0m  %s\n' "$1"; }
warn() { printf '  \033[33mDİQQƏT\033[0m %s\n' "$1"; }

[ -f .env ] || { echo ".env yoxdur"; exit 1; }

KEY=$(grep '^GROQ_API_KEY=' .env | tail -1 | cut -d= -f2-)
[ -n "$KEY" ] || { bad "GROQ_API_KEY boşdur"; exit 1; }

# Defolt dəyərlər config.py ilə eyni olmalıdır — .env-də yazılmayıbsa kod
# onları işlədir və yoxlama da onlara baxmalıdır.
MAIN=$(grep '^GROQ_MODEL=' .env | tail -1 | cut -d= -f2-)
EXTRACT=$(grep '^EXTRACT_MODEL=' .env | tail -1 | cut -d= -f2-)
[ -n "$MAIN" ]    || MAIN="openai/gpt-oss-120b"
[ -n "$EXTRACT" ] || EXTRACT="openai/gpt-oss-20b"

LIST=$(curl -s --max-time 20 https://api.groq.com/openai/v1/models \
        -H "Authorization: Bearer $KEY")

if [ -z "$LIST" ]; then
  warn "provayder cavab vermədi — yoxlama atlandı (şəbəkə?)"
  exit 0
fi
if printf '%s' "$LIST" | grep -q '"invalid_api_key"\|"authentication'; then
  bad "GROQ_API_KEY qəbul edilmədi"
  exit 1
fi

AVAILABLE=$(printf '%s' "$LIST" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)

FAIL=0
for pair in "GROQ_MODEL:$MAIN" "EXTRACT_MODEL:$EXTRACT"; do
  name="${pair%%:*}"; model="${pair#*:}"
  if printf '%s\n' "$AVAILABLE" | grep -qx "$model"; then
    ok "$name = $model"
  else
    bad "$name = $model — provayderdə YOXDUR"
    FAIL=$((FAIL+1))
  fi
done

if [ "$FAIL" -gt 0 ]; then
  echo
  echo "Mövcud modellər (səs/təhlükəsizlik modelləri çıxarılıb):"
  printf '%s\n' "$AVAILABLE" \
    | grep -vE 'whisper|orpheus|prompt-guard|safeguard' \
    | sed 's/^/  /'
  echo
  echo ".env-də GROQ_MODEL və ya EXTRACT_MODEL dəyərini yenilə, sonra:"
  echo "  docker compose -f docker-compose.prod.yml up -d --force-recreate backend"
  exit 1
fi
