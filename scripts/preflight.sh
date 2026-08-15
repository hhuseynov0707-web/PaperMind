#!/usr/bin/env bash
# Deploy-dan ƏVVƏL işlət:  bash scripts/preflight.sh
# .env-i və produksiya konfiqurasiyasını yoxlayır. Heç nə dəyişmir.

set -uo pipefail
cd "$(dirname "$0")/.."

PASS=0; FAIL=0; WARN=0
ok()   { printf '  \033[32mOK\033[0m    %s\n' "$1"; PASS=$((PASS+1)); }
bad()  { printf '  \033[31mXƏTA\033[0m  %s\n' "$1"; FAIL=$((FAIL+1)); }
warn() { printf '  \033[33mDİQQƏT\033[0m %s\n' "$1"; WARN=$((WARN+1)); }

echo "PaperMind — deploy hazırlığı yoxlaması"
echo "======================================"

# ---------- .env ----------
echo; echo ".env faylı"
if [ ! -f .env ]; then
  bad ".env yoxdur — 'cp .env.example .env' işlət və doldur"
else
  ok ".env mövcuddur"
  set -a; . ./.env 2>/dev/null || true; set +a

  [ -n "${DOMAIN:-}" ] && [ "${DOMAIN}" != "papermind.example.com" ] \
    && ok "DOMAIN: ${DOMAIN}" || bad "DOMAIN doldurulmayıb (nümunə dəyər qalıb)"

  [ -n "${GROQ_API_KEY:-}" ] && ok "GROQ_API_KEY var" || bad "GROQ_API_KEY boşdur — RAG işləməyəcək"

  if [ -z "${ADMIN_API_KEY:-}" ]; then
    bad "ADMIN_API_KEY boşdur — yazma endpoint-ləri 503 qaytaracaq"
  elif [ ${#ADMIN_API_KEY} -lt 32 ]; then
    bad "ADMIN_API_KEY qısadır (${#ADMIN_API_KEY} simvol) — 'openssl rand -hex 32' işlət"
  else
    ok "ADMIN_API_KEY güclüdür (${#ADMIN_API_KEY} simvol)"
  fi

  if [ "${POSTGRES_PASSWORD:-elmradari}" = "elmradari" ]; then
    bad "POSTGRES_PASSWORD default dəyərdədir — dəyiş"
  else
    ok "POSTGRES_PASSWORD dəyişdirilib"
  fi

  [ -n "${CONTACT_EMAIL:-}" ] && ok "CONTACT_EMAIL var (Crossref nəzakətli hovuzu)" \
    || warn "CONTACT_EMAIL boşdur — Crossref limitləri daha sərt ola bilər"
fi

# ---------- git ----------
echo; echo "Sirlərin qorunması"
if git rev-parse --git-dir > /dev/null 2>&1; then
  if git check-ignore -q .env 2>/dev/null; then
    ok ".env .gitignore-dadır"
  else
    bad ".env git tərəfindən izlənir — açarların sızma riski!"
  fi
else
  warn "git repo deyil — .env-in təsadüfən paylaşılmamasına diqqət et"
fi

# ---------- produksiya konfiqurasiyası ----------
echo; echo "Produksiya konfiqurasiyası"
if [ ! -f docker-compose.prod.yml ]; then
  bad "docker-compose.prod.yml yoxdur"
else
  if docker compose -f docker-compose.prod.yml config > /tmp/pm_cfg.yml 2>/dev/null; then
    ok "docker-compose.prod.yml sintaksisi düzgündür"
    PORTS=$(grep -c 'published:' /tmp/pm_cfg.yml || true)
    PUBLISHED=$(grep 'published:' /tmp/pm_cfg.yml | tr -d ' "' | sed 's/published://' | sort -u | tr '\n' ' ')
    if [ "$PORTS" -eq 2 ] && [ "$PUBLISHED" = "443 80 " -o "$PUBLISHED" = "80 443 " ]; then
      ok "yalnız 80 və 443 internetə açıqdır"
    else
      bad "gözlənilməz açıq portlar: ${PUBLISHED}— postgres/redis/n8n bağlı olmalıdır"
    fi
    grep -q 'PUBLIC_MODE: "true"' /tmp/pm_cfg.yml && ok "PUBLIC_MODE aktivdir" \
      || bad "PUBLIC_MODE aktiv deyil — yazma endpoint-ləri qorunmayacaq"
    rm -f /tmp/pm_cfg.yml
  else
    bad "docker-compose.prod.yml validasiyadan keçmir (DOMAIN/POSTGRES_PASSWORD boş ola bilər)"
  fi
fi

[ -f Caddyfile ] && ok "Caddyfile mövcuddur" || bad "Caddyfile yoxdur — HTTPS qurulmayacaq"

# ---------- DNS ----------
echo; echo "Şəbəkə"
if [ -n "${DOMAIN:-}" ] && [ "${DOMAIN}" != "papermind.example.com" ]; then
  RESOLVED="$(getent hosts "$DOMAIN" 2>/dev/null | awk '{print $1; exit}')"
  if [ -z "$RESOLVED" ]; then
    warn "DOMAIN həll olunmur — A qeydini yoxla (Let's Encrypt bunsuz sertifikat verməz)"
  else
    # «Həll olunur» kifayət deyil — BU serverə həll olunmalıdır. Domen başqa
    # ünvana baxırsa Let's Encrypt doğrulaması keçmir və sayt HTTPS-siz qalır.
    # Əvvəl xarici əks-sədadan soruşulur (Oracle kimi NAT-lı mühitlərdə lokal
    # interfeys özəl IP göstərir), alınmasa marşrut cədvəlinə baxılır.
    MYIP="$(curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null \
      || ip route get 1.1.1.1 2>/dev/null \
         | awk '{ for (i = 1; i < NF; i++) if ($i == "src") { print $(i+1); exit } }')"
    if [ -z "$MYIP" ]; then
      warn "DOMAIN → ${RESOLVED} (serverin öz IP-si təyin edilmədi, tutuşdurma atlandı)"
    elif [ "$RESOLVED" = "$MYIP" ]; then
      ok "DOMAIN bu serverə yönəlib: ${RESOLVED}"
    else
      bad "DOMAIN BAŞQA ünvana yönəlib: ${RESOLVED} (bu server: ${MYIP}) — Let's Encrypt sertifikat verməyəcək"
    fi
  fi
fi

# ---------- resurslar ----------
echo; echo "Resurslar"
if [ -r /proc/meminfo ]; then
  MB=$(( $(awk '/MemTotal/ {print $2}' /proc/meminfo) / 1024 ))
  [ "$MB" -ge 1900 ] && ok "RAM: ${MB} MB" || bad "RAM: ${MB} MB — ən azı 2 GB lazımdır"
fi

echo
echo "======================================"
printf 'Nəticə: \033[32m%d OK\033[0m · \033[33m%d diqqət\033[0m · \033[31m%d xəta\033[0m\n' "$PASS" "$WARN" "$FAIL"
[ "$FAIL" -eq 0 ] && echo "Deploy edə bilərsən." || echo "Xətaları düzəlt, sonra deploy et."
exit $(( FAIL > 0 ? 1 : 0 ))
