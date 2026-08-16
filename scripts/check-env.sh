#!/usr/bin/env bash
# .env-i diaqnoz edir — dəyərləri AÇIQLAMADAN.
#
# Niyə lazımdır: fayl gözlə baxanda dolu görünür, amma skript «boşdur» deyir.
# Səbəb demək olar ki, həmişə görünməyən simvoldur:
#   - sətir başında boşluq  ->  `grep "^KEY="` uyğun gəlmir
#   - sonda \r (CRLF)        ->  dəyər "abc\r" olur və müqayisələr sürüşür
#   - dublikat sətir         ->  sonuncu qalib gəlir, sən birincisinə baxırsan
#
# Dəyərin ÖZÜ göstərilmir — yalnız uzunluq və ilk 4 simvol.
#
#     cd /root/papermind; bash scripts/check-env.sh

set -uo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { echo ".env yoxdur"; exit 1; }

KEYS="GROQ_API_KEY ADMIN_API_KEY POSTGRES_PASSWORD DOMAIN PAYMENT_PROVIDER
      PADDLE_CLIENT_TOKEN PADDLE_WEBHOOK_SECRET PADDLE_PRICE_ID_PRO
      PADDLE_ENVIRONMENT PUBLIC_BASE_URL"

printf '\n%-24s %-6s %-6s %-8s %s\n' "AÇAR" "SƏTİR" "UZUN" "BAŞLAYIR" "QEYD"
printf '%s\n' "--------------------------------------------------------------------"

for k in $KEYS; do
  # Sətir NÖMRƏSİ sərt uyğunluqla axtarılır — skriptlərin işlətdiyi qayda ilə eyni.
  line=$(grep -n "^${k}=" .env | tail -1 | cut -d: -f1)
  count=$(grep -c "^${k}=" .env)
  # Boşluqla başlayan variant AYRICA axtarılır: gözlə görünmür, amma
  # `^KEY=` şablonuna uyğun gəlmədiyi üçün dəyər "yoxdur" sayılır.
  loose=$(grep -cE "^[[:space:]]+${k}=" .env)

  note=""
  if [ -z "$line" ]; then
    if [ "$loose" -gt 0 ]; then
      note="SƏTİR BAŞINDA BOŞLUQ VAR — buna görə oxunmur"
    else
      note="yoxdur"
    fi
    printf '%-24s %-6s %-6s %-8s %s\n' "$k" "-" "-" "-" "$note"
    continue
  fi

  raw=$(sed -n "${line}p" .env)
  val="${raw#*=}"
  len=${#val}
  head4="${val:0:4}"

  case "$raw" in
    *$'\r') note="SONDA \\r VAR (CRLF) — dəyər korlanır" ;;
  esac
  [ "$count" -gt 1 ] && note="${note}${note:+; }$count dəfə yazılıb (sonuncu qalib gəlir)"
  [ "$len" -eq 0 ] && note="${note}${note:+; }BOŞDUR"
  case "$val" in
    *' '*) note="${note}${note:+; }içində BOŞLUQ var" ;;
  esac

  printf '%-24s %-6s %-6s %-8s %s\n' "$k" "$line" "$len" "$head4" "${note:-ok}"
done

echo
echo "Etibarsız formalı sətirlər (AD=dəyər, şərh və boş sətirdən başqa):"
bad=$(grep -nvE '^[[:space:]]*($|#|[A-Za-z_][A-Za-z0-9_]*=)' .env | head -10)
if [ -n "$bad" ]; then
  # Yalnız sətir nömrəsi və ilk 30 simvol — sirr sızmasın.
  printf '%s\n' "$bad" | cut -c1-40
  echo
  echo "Bu sətirlər Docker-in .env-i oxumasını TAMAMİLƏ dayandırır."
else
  echo "  yoxdur"
fi

echo
echo "Konteynerin gördüyü (işləyirsə):"
for k in PAYMENT_PROVIDER PADDLE_CLIENT_TOKEN PADDLE_PRICE_ID_PRO; do
  v=$(docker compose -f docker-compose.prod.yml exec -T backend printenv "$k" 2>/dev/null | tr -d '\r\n')
  if [ -n "$v" ]; then
    printf '  %-24s var (%s simvol)\n' "$k" "${#v}"
  else
    printf '  %-24s YOXDUR\n' "$k"
  fi
done
echo
