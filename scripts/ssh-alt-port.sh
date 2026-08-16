#!/usr/bin/env bash
# SSH-i ƏLAVƏ portda da dinlədir (defolt 2222).
#
# Niyə lazımdır: bəzi internet provayderləri ÇIXIŞ 22-ci portunu bloklayır.
# Server tamamilə sağlam olur — sshd dinləyir, firewall açıqdır — amma
# istifadəçi qoşula bilmir və səbəb heç bir logda görünmür. Bunu ayırd etmək
# üçün istənilən məlum SSH host-una baxmaq kifayətdir:
#     Test-NetConnection github.com -Port 22
# O da bağlıdırsa, problem şəbəkəndədir, serverdə yox.
#
# İşlətmək (serverdə, root ilə):
#     bash scripts/ssh-alt-port.sh
#     bash scripts/ssh-alt-port.sh 8022      # başqa port
#
# 22-ci port SAXLANILIR. Məqsəd alternativ yol açmaqdır, mövcud yolu bağlamaq
# yox — səhv olarsa özünü tamamilə kilidləməyəsən.

set -euo pipefail

PORT="${1:-2222}"

info() { printf '\n\033[36m==> %s\033[0m\n' "$1"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }

[ "$(id -u)" -eq 0 ] || { echo "root ilə işlət"; exit 1; }

case "$PORT" in
  ''|*[!0-9]*) echo "Port rəqəm olmalıdır: $PORT"; exit 1 ;;
esac
[ "$PORT" -ge 1024 ] && [ "$PORT" -le 65535 ] || { echo "Port 1024-65535 aralığında olsun"; exit 1; }

info "1/4 · Mövcud vəziyyət"
SOCKET_MODE=no
if systemctl is-active --quiet ssh.socket 2>/dev/null; then
  SOCKET_MODE=yes
  ok "ssh.socket aktivdir — port socket unit-i ilə idarə olunur"
else
  ok "klassik sshd rejimi — port sshd_config-dədir"
fi

info "2/4 · Port $PORT əlavə olunur"
if [ "$SOCKET_MODE" = yes ]; then
  # Ubuntu 24.04+ SSH-i socket activation ilə işlədir. Bu rejimdə
  # sshd_config-dəki `Port` direktivi NƏZƏRƏ ALINMIR — dinlənilən portları
  # yalnız socket unit-i təyin edir. Bunu bilməyib sshd_config-i dəyişmək
  # ən çox vaxt itirilən yerdir.
  mkdir -p /etc/systemd/system/ssh.socket.d
  # Ünvanlar AÇIQ yazılır. Yalnız `ListenStream=22` yazmaq TƏHLÜKƏLİDİR:
  # systemd onu tək IPv6 soketi kimi yaradır və sistemdə `bindv6only`
  # aktivdirsə IPv4 girişi TAMAMİLƏ ölür. Bir dəfə məhz belə oldu — server
  # sağlam görünürdü, `ss` isə yalnız [::]:22 göstərirdi.
  cat > /etc/systemd/system/ssh.socket.d/10-alt-port.conf <<EOF
[Socket]
# Boş dəyər siyahını sıfırlayır — olmasa defolt 22 ilə dublikat yaranır.
ListenStream=
ListenStream=0.0.0.0:22
ListenStream=[::]:22
ListenStream=0.0.0.0:$PORT
ListenStream=[::]:$PORT
EOF
  systemctl daemon-reload
  systemctl restart ssh.socket
  ok "socket drop-in yazıldı və yenidən başladıldı"
else
  mkdir -p /etc/ssh/sshd_config.d
  cat > /etc/ssh/sshd_config.d/10-alt-port.conf <<EOF
Port 22
Port $PORT
EOF
  # Konfiqurasiya səhv olsa sshd qalxmır və o zaman heç bir yolla girmək
  # mümkün olmur. Ona görə ƏVVƏLCƏ yoxlanılır.
  if ! sshd -t; then
    rm -f /etc/ssh/sshd_config.d/10-alt-port.conf
    echo "sshd konfiqurasiyası validasiyadan keçmədi — dəyişiklik geri alındı"
    exit 1
  fi
  systemctl restart ssh
  ok "sshd_config.d yazıldı və servis yenidən başladıldı"
fi

info "3/4 · Firewall"
# Hetzner-in Ubuntu image-ində INPUT siyasəti ACCEPT-dir və qadağa qaydası
# yoxdur, yəni adətən heç nə lazım deyil. Yenə də qadağa varsa icazə əlavə olunur.
if iptables -L INPUT -n 2>/dev/null | awk 'NR>2 && ($1=="REJECT" || $1=="DROP")' | grep -q .; then
  if ! iptables -C INPUT -p tcp --dport "$PORT" -j ACCEPT 2>/dev/null; then
    iptables -I INPUT 1 -p tcp --dport "$PORT" -j ACCEPT
    command -v netfilter-persistent >/dev/null && netfilter-persistent save >/dev/null 2>&1 || true
    ok "iptables-də port $PORT açıldı"
  else
    ok "port $PORT artıq icazəlidir"
  fi
else
  ok "INPUT zəncirində qadağa yoxdur — dəyişiklik lazım deyil"
fi

info "4/4 · Yoxlama"
sleep 1
# IPv4 AYRICA yoxlanılır: yalnız IPv6-da dinləmək «işləyir» kimi görünür,
# amma IPv4 müştəri qoşula bilmir və səbəb heç bir logda görünmür.
for p in 22 "$PORT"; do
  if ss -tln4 | awk '{print $4}' | grep -qE "[:.]${p}\$"; then
    ok "port $p — IPv4 dinlənilir"
  else
    warn "port $p — IPv4 DİNLƏNİLMİR (yalnız IPv6 varsa, IPv4 müştəri qoşula bilməz)"
  fi
done
echo
ss -tln | awk 'NR==1 || $4 ~ /:(22|'"$PORT"')$/'

cat <<NEXT

Öz kompüterindən yoxla:
    Test-NetConnection -ComputerName <SERVER_IP> -Port $PORT -InformationLevel Quiet

True qayıtsa belə qoşul:
    ssh -p $PORT -i ~/.ssh/papermind root@<SERVER_IP>

Qeyd: 22-ci port da açıq qalır. Provayder blokunu keçmək üçün $PORT işlədilir;
server tərəfdə heç nə bağlanmayıb.
NEXT
