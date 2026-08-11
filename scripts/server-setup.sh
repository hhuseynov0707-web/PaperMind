#!/usr/bin/env bash
# Oracle Cloud (Ubuntu 22.04 ARM) serverini PaperMind üçün hazırlayır.
# Serverdə işlət:  bash scripts/server-setup.sh
#
# Nə edir: Docker qurur, firewall-un HƏR İKİ səviyyəsini açır, swap yaradır.
# İdempotentdir — təkrar işlətmək təhlükəsizdir.

set -euo pipefail

info() { printf '\n\033[36m==> %s\033[0m\n' "$1"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }

[ "$(id -u)" -eq 0 ] && SUDO="" || SUDO="sudo"

info "1/5 · Sistem yenilənir"
$SUDO apt-get update -qq
ok "paket siyahısı yeniləndi"

info "2/5 · Docker"
if command -v docker > /dev/null 2>&1; then
  ok "Docker artıq quraşdırılıb ($(docker --version))"
else
  curl -fsSL https://get.docker.com | $SUDO sh
  $SUDO usermod -aG docker "$USER"
  ok "Docker quruldu — qrup dəyişikliyi üçün sessiyanı yenidən aç"
fi

info "3/5 · Firewall (Oracle-da İKİ səviyyə var)"
# (a) Serverin öz iptables-ı. Ubuntu image-də 80/443 default olaraq BAĞLIDIR.
for port in 80 443; do
  if $SUDO iptables -C INPUT -m state --state NEW -p tcp --dport "$port" -j ACCEPT 2>/dev/null; then
    ok "port $port artıq açıqdır"
  else
    $SUDO iptables -I INPUT 6 -m state --state NEW -p tcp --dport "$port" -j ACCEPT
    ok "port $port açıldı"
  fi
done
$SUDO apt-get install -y -qq iptables-persistent > /dev/null 2>&1 || true
$SUDO netfilter-persistent save > /dev/null 2>&1 || true
ok "qaydalar restartdan sonra da qalacaq"

cat <<'REMINDER'

  ⚠ DİQQƏT — bu skript yalnız (a) hissəsini etdi.
    (b) Oracle KONSOLUNDA da açmalısan:
        Networking → Virtual Cloud Networks → <VCN> → Security Lists
        → Default Security List → Add Ingress Rules
          Source: 0.0.0.0/0   IP Protocol: TCP   Destination Port: 80,443
    Yalnız birini etmək saytın açılmamasına səbəb olur və səbəb heç yerdə görünmür.

REMINDER

info "4/5 · Swap (yaddaş qəfil dolarsa ehtiyat)"
if $SUDO swapon --show | grep -q .; then
  ok "swap artıq mövcuddur"
else
  $SUDO fallocate -l 2G /swapfile
  $SUDO chmod 600 /swapfile
  $SUDO mkswap /swapfile > /dev/null
  $SUDO swapon /swapfile
  echo '/swapfile none swap sw 0 0' | $SUDO tee -a /etc/fstab > /dev/null
  ok "2 GB swap yaradıldı"
fi

info "5/5 · Yoxlama"
echo "  arxitektura : $(uname -m)"
echo "  RAM         : $(( $(awk '/MemTotal/ {print $2}' /proc/meminfo) / 1024 )) MB"
echo "  boş disk    : $(df -h / | awk 'NR==2 {print $4}')"
echo "  Docker      : $(docker --version 2>/dev/null || echo 'sessiyanı yenidən aç')"

cat <<'NEXT'

Server hazırdır. Növbəti addımlar:

  1. Faylları köçür (öz kompüterindən):
       scp -r papermind ubuntu@<SERVER_IP>:~/

  2. Serverdə:
       cd ~/papermind
       cp .env.example .env && nano .env      # DOMAIN, GROQ_API_KEY, parollar
       openssl rand -hex 32                   # ADMIN_API_KEY üçün
       bash scripts/preflight.sh              # hamısı OK olmalıdır
       docker compose -f docker-compose.prod.yml up -d --build

NEXT
