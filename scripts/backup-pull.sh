#!/usr/bin/env bash
# Şifrələnmiş yedəkləri serverdən BU kompüterə çəkir və AÇILDIĞINI yoxlayır.
#
#   bash scripts/backup-pull.sh
#
# ## Niyə bu skript var
#
# Yedəklər bazanın olduğu serverdə idi. Server itsə (disk nasazlığı, hesabın
# bağlanması, silinmiş instans) yedəklər də onunla gedirdi — yəni yedək
# əslində fəlakətdən qorumurdu, yalnız «səhvən sildim» halını örtürdü.
#
# Bu skript nüsxəni FƏRQLİ fiziki yerə gətirir. Bulud kovası qurulana qədər
# bu, tam işləyən kənar surətdir; qurulandan sonra da ikinci qat kimi qalır.
#
# ## Ən vacib hissə: açılma yoxlanışı
#
# Yedəyin ən çox rast gəlinən nasazlığı «fayl var, amma açılmır»dır — və bu,
# ancaq bərpa lazım olan gün üzə çıxır. Ona görə hər çəkilən fayl DƏRHAL
# açılıb yoxlanılır: gzip başlığı düzgündürmü, içində SQL varmı.
#
# Gizli açar yalnız burada olduğu üçün bu yoxlamanı serverdə etmək mümkün
# deyil — dizayn qəsdən belədir.

set -uo pipefail

HOST="${PM_HOST:-root@2.28.22.89}"
KEY="${PM_KEY:-$HOME/.ssh/papermind}"
REMOTE_DIR="${PM_BACKUP_DIR:-/root/papermind-backups}"
LOCAL_DIR="${PM_LOCAL_BACKUP_DIR:-$HOME/papermind-backups}"
KEEP="${PM_LOCAL_KEEP:-30}"

G='\033[32m'; R='\033[31m'; Y='\033[33m'; N='\033[0m'
ok()   { printf "  ${G}OK${N}    %s\n" "$1"; }
bad()  { printf "  ${R}XƏTA${N}  %s\n" "$1"; FAIL=$((FAIL+1)); }
warn() { printf "  ${Y}DİQQƏT${N} %s\n" "$1"; }
FAIL=0

mkdir -p "$LOCAL_DIR"

echo "==> Serverdəki nüsxələr"
SSH="ssh -o ConnectTimeout=20 -i $KEY $HOST"
REMOTE=$($SSH "ls -1 $REMOTE_DIR/papermind-*.sql.gz.gpg 2>/dev/null" | tr -d '\r')
if [ -z "$REMOTE" ]; then
  bad "serverdə şifrələnmiş nüsxə tapılmadı ($REMOTE_DIR)"
  echo "      Serverdə bir dəfə işlət: cd ~/papermind && bash scripts/backup.sh"
  exit 1
fi
echo "$REMOTE" | wc -l | sed 's/^/  serverdə: /'

echo
echo "==> Çəkilir"
NEW=0
for path in $REMOTE; do
  name=$(basename "$path")
  if [ -f "$LOCAL_DIR/$name" ]; then continue; fi
  if scp -o ConnectTimeout=20 -i "$KEY" "$HOST:$path" "$LOCAL_DIR/$name" >/dev/null 2>&1; then
    ok "$name ($(du -h "$LOCAL_DIR/$name" | cut -f1))"
    NEW=$((NEW+1))
  else
    bad "$name çəkilmədi"
  fi
done
[ "$NEW" -eq 0 ] && echo "  yeni nüsxə yoxdur"

echo
echo "==> Açılma yoxlanışı (ən son nüsxə)"
LATEST=$(ls -1t "$LOCAL_DIR"/papermind-*.sql.gz.gpg 2>/dev/null | head -1)
if [ -z "$LATEST" ]; then
  bad "yerli nüsxə yoxdur"
else
  # Tam açmırıq — yalnız başlanğıcı. 25 MB-lıq faylı hər dəfə tam açmaq
  # lazımsızdır; korlanma və ya açar uyğunsuzluğu ilk baytlarda üzə çıxır.
  HEAD=$(gpg --batch --quiet --decrypt "$LATEST" 2>/dev/null | gunzip 2>/dev/null | head -c 400)
  if [ -z "$HEAD" ]; then
    bad "AÇILMADI: $(basename "$LATEST")"
    echo "      Gizli açar bu kompüterdədirmi?  gpg --list-secret-keys"
  elif echo "$HEAD" | grep -qiE "PostgreSQL database dump|^SET |CREATE TABLE"; then
    ok "$(basename "$LATEST") — açıldı və içində SQL var"
  else
    bad "açıldı, amma məzmun SQL dump-a oxşamır"
  fi
fi

echo
echo "==> Köhnə yerli nüsxələr"
ls -1t "$LOCAL_DIR"/papermind-*.sql.gz.gpg 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r old; do
  rm -f "$old"; echo "  silindi: $(basename "$old")"
done
TOTAL=$(ls -1 "$LOCAL_DIR"/papermind-*.sql.gz.gpg 2>/dev/null | wc -l)

echo
echo "======================================"
if [ "$FAIL" -eq 0 ]; then
  printf "Nəticə: ${G}hamısı OK${N}  ·  yerli nüsxə: %s  ·  %s\n" "$TOTAL" "$LOCAL_DIR"
  echo
  echo "Bərpanı sınamaq üçün:  bash scripts/restore-test.sh"
else
  printf "Nəticə: ${R}%s xəta${N}\n" "$FAIL"
fi
exit "$FAIL"
