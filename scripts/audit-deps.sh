#!/usr/bin/env bash
# Asılılıq zəifliyi taraması.
#
#   bash scripts/audit-deps.sh        # istehsalatda İŞLƏYƏN dəsti yoxlayır
#   bash scripts/audit-deps.sh --env  # LOKAL quraşdırılmış mühiti yoxlayır
#
# Niyə serverdə işləyir:
#   `uvloop` yalnız Linux üçündür. Windows-da `pip-audit` asılılıqları həll
#   etməyə çalışanda onu qurmağa cəhd edir və düşür. Üstəlik lokal
#   `requirements.txt` yalnız 17 BİRBAŞA paketi sadalayır — istehsalatda isə
#   transitiv olanlarla birlikdə 62 paket işləyir. Zəiflik çox vaxt məhz
#   transitiv paketdə olur, ona görə əsl cavab yalnız orada alınır.
#
# İstehsalata TOXUNMUR: tarama birdəfəlik konteynerdə aparılır, produksiya
# konteynerinə heç nə quraşdırılmır.
set -uo pipefail

HOST="${PM_HOST:-root@2.28.22.89}"
KEY="${PM_KEY:-$HOME/.ssh/papermind}"
DIR="${PM_DIR:-/root/papermind}"
IMG="python:3.12-slim"

cd "$(dirname "$0")/.." || exit 1

# `-r fayl` rejimi Windows-da İŞLƏMİR və işləyə də bilməz: pip-audit faylı
# oxuyanda asılılıqları HƏLL EDİR, həll isə `uvloop`-u qurmağa çalışır —
# o paket yalnız Linux üçündür. `--no-deps` da kömək etmir, çünki quraşdırma
# addımı yenə işə düşür.
#
# Ona görə lokal variant faylı yox, MÜHİTİ yoxlayır: nə quraşdırılıbsa onu.
# Bu, istehsalat dəsti DEYİL — orada fərqli paketlər ola bilər, ona görə
# əsas rejim aşağıdakıdır.
if [ "${1:-}" = "--env" ]; then
  echo "==> Lokal quraşdırılmış mühit (istehsalat DEYİL)"
  python -m pip_audit --progress-spinner off
  exit $?
fi

echo "==> İstehsalatda işləyən dəst (transitiv daxil)"
ssh -o ConnectTimeout=20 -i "$KEY" "$HOST" "
  set -e
  cd $DIR
  docker compose -f docker-compose.prod.yml exec -T backend pip freeze > /tmp/pf.txt 2>/dev/null
  echo \"  paket sayı: \$(wc -l < /tmp/pf.txt)\"
  docker run --rm -v /tmp/pf.txt:/pf.txt:ro $IMG sh -c \
    'pip install -q pip-audit 2>/dev/null && pip-audit -r /pf.txt --no-deps --progress-spinner off' \
    2>&1 | grep -viE '^WARNING:pip_audit'
  docker image rm -f $IMG >/dev/null 2>&1 || true
  rm -f /tmp/pf.txt
"
