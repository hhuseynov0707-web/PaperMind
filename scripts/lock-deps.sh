#!/usr/bin/env bash
# `requirements.in` -> `requirements.txt` (bütün paketlər + SHA-256 həshləri).
#
#   bash scripts/lock-deps.sh
#
# ## Niyə serverdə, birbaşa lokalda yox
#
# `pip-compile` asılılıqları İŞLƏDİYİ PLATFORMA üçün həll edir. İstehsalat
# `python:3.11-slim` (Linux) üzərindədir və `uvicorn[standard]` orada
# `uvloop` ilə birlikdə gəlir — Windows-da isə həmin paket ümumiyyətlə
# qurulmur. Lokalda qursaq, kilid istehsalatda quraşdırılan dəstlə
# UYĞUNSUZ olardı və build həsh xətası ilə düşərdi.
#
# Ona görə kilid istehsalatın Python versiyası ilə eyni konteynerdə qurulur.
# İstehsalat konteynerinə TOXUNULMUR — ayrıca, birdəfəlik konteyner işlədilir.
set -uo pipefail

HOST="${PM_HOST:-root@2.28.22.89}"
KEY="${PM_KEY:-$HOME/.ssh/papermind}"
IMG="${PM_PY_IMAGE:-python:3.11-slim}"    # Dockerfile ilə EYNİ olmalıdır

cd "$(dirname "$0")/.." || exit 1

[ -f backend/requirements.in ] || { echo "backend/requirements.in tapılmadı"; exit 1; }

echo "==> requirements.in serverə göndərilir"
scp -o ConnectTimeout=20 -i "$KEY" backend/requirements.in "$HOST:/tmp/requirements.in" >/dev/null || {
  echo "  serverə qoşulmaq alınmadı"; exit 1; }

echo "==> Kilid qurulur ($IMG) — bir neçə dəqiqə çəkə bilər"
ssh -o ConnectTimeout=20 -i "$KEY" "$HOST" "
  docker run --rm -v /tmp:/w -w /w $IMG sh -c '
    pip install -q pip-tools 2>/dev/null &&
    pip-compile --generate-hashes --strip-extras --quiet \
      --output-file /w/requirements.txt /w/requirements.in
  '
" || { echo "  kilid qurulmadı"; exit 1; }

echo "==> Nəticə geri gətirilir"
scp -o ConnectTimeout=20 -i "$KEY" "$HOST:/tmp/requirements.txt" backend/requirements.txt >/dev/null || {
  echo "  fayl gətirilmədi"; exit 1; }

ssh -o ConnectTimeout=20 -i "$KEY" "$HOST" "rm -f /tmp/requirements.in /tmp/requirements.txt" >/dev/null 2>&1

PKGS=$(grep -cE '^[a-zA-Z0-9]' backend/requirements.txt)
HASHES=$(grep -c -- '--hash=sha256:' backend/requirements.txt)
echo
echo "  paket: $PKGS   |   həsh: $HASHES"
[ "$HASHES" -gt 0 ] && echo "  OK — kilid həshlidir" || { echo "  XƏTA: həsh yoxdur"; exit 1; }
echo
echo "  Növbəti: testlər, sonra 'bash scripts/ship.sh -m \"...\"'"
