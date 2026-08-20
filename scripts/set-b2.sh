#!/usr/bin/env bash
# Backblaze B2 açarlarını qəbul edir və kənar yedəyi qoşur.
#
# SERVERDƏ işlədilir:
#   ssh -i ~/.ssh/papermind root@2.28.22.89
#   cd ~/papermind && bash scripts/set-b2.sh
#
# Açarlar YALNIZ burada yazılır. Onları söhbətə, e-poçta və ya sənədə
# köçürmə: bir dəfə kənara çıxan açar geri qaytarıla bilməz, yalnız ləğv
# edilə bilər.
#
# ## Əvvəlcə B2-də nə yaratmalısan
#
#   1. Buckets -> Create a Bucket
#        Files in Bucket: PRIVATE  (mütləq — Public seçsən yedəklər
#        internetdən oxuna bilər; şifrəli olsalar da bunu vermək lazım deyil)
#   2. Application Keys -> Add a New Application Key
#        - Allow access to Bucket(s): yalnız YUXARIDAKI bucket
#        - Type of Access: Read and Write
#        Ekranda `keyID` və `applicationKey` görünür. `applicationKey`
#        BİR DƏFƏ göstərilir — pəncərəni bağlamazdan əvvəl bura yaz.

set -uo pipefail
cd "$(dirname "$0")/.."

G='\033[32m'; R='\033[31m'; Y='\033[33m'; N='\033[0m'
ok()  { printf "  ${G}OK${N}    %s\n" "$1"; }
bad() { printf "  ${R}XƏTA${N}  %s\n" "$1"; }

command -v rclone >/dev/null 2>&1 || { bad "rclone yoxdur: apt-get install -y rclone"; exit 1; }

# Sual mətni STDERR-ə gedir. stdout-a getsəydi və funksiya `$(...)` ilə
# çağırılsaydı, sualın özü dəyərin içinə düşərdi — bu səhv bu layihədə
# artıq bir dəfə baş verib (Paddle açarları).
ask() {
  local prompt="$1" secret="${2:-no}" value=""
  while [ -z "$value" ]; do
    printf "%s: " "$prompt" >&2
    if [ "$secret" = yes ]; then read -r value; printf "\n" >&2; else read -r value; fi
    # Konsolda kopyalayanda başa/sona boşluq və görünməz simvol düşür.
    value="$(printf '%s' "$value" | tr -d '[:space:]')"
    [ -z "$value" ] && printf "  boş ola bilməz, yenidən yaz\n" >&2
  done
  printf '%s' "$value"
}

echo
echo "Backblaze B2 açarları (B2 -> Application Keys ekranından)"
echo

KEY_ID=$(ask "keyID")
APP_KEY=$(ask "applicationKey" yes)

echo
echo "Qoşulma yoxlanılır…"
# Config-i əvvəlcə YAZIRIQ, sonra sınayırıq. Yanlış olsa aşağıda silinir —
# yarımçıq konfiqurasiya qalmasın.
rclone config delete b2 >/dev/null 2>&1 || true
rclone config create b2 b2 account "$KEY_ID" key "$APP_KEY" >/dev/null 2>&1

BUCKETS=$(rclone lsd b2: 2>&1)
if echo "$BUCKETS" | grep -qiE "error|failed|401|unauthorized"; then
  bad "açarlar qəbul olunmadı"
  echo "$BUCKETS" | head -3 | sed 's/^/      /'
  rclone config delete b2 >/dev/null 2>&1
  exit 1
fi

NAMES=$(echo "$BUCKETS" | awk '{print $NF}' | grep -v '^$')
if [ -z "$NAMES" ]; then
  bad "hesabda bucket yoxdur — əvvəlcə B2-də PRIVATE bucket yarat"
  rclone config delete b2 >/dev/null 2>&1
  exit 1
fi
ok "qoşuldu"
echo "  mövcud bucket-lər:"
echo "$NAMES" | sed 's/^/    /'
echo

BUCKET=$(ask "hansı bucket işlədilsin")
if ! echo "$NAMES" | grep -qx "$BUCKET"; then
  bad "belə bucket yoxdur: $BUCKET"
  exit 1
fi

REMOTE="b2:$BUCKET/papermind"

echo
echo "Yazma yoxlanılır…"
# «Açar qəbul olundu» ilə «yaza bilirəm» eyni şey deyil: yalnız oxuma
# icazəsi olan açar da siyahını göstərir, amma yedək göndərə bilmir.
TMP=$(mktemp); echo "papermind-yazma-sinagi $(date -u +%FT%TZ)" > "$TMP"
if rclone copyto "$TMP" "$REMOTE/.write-test" >/dev/null 2>&1; then
  ok "yazma işləyir"
  rclone delete "$REMOTE/.write-test" >/dev/null 2>&1
else
  bad "yazma alınmadı — açarın icazəsi «Read and Write» olmalıdır"
  rm -f "$TMP"; exit 1
fi
rm -f "$TMP"

# --- .env ----------------------------------------------------------------
touch .env
sed -i '/^BACKUP_REMOTE=/d;/^BACKUP_REMOTE_KEEP_DAYS=/d' .env
{
  echo "BACKUP_REMOTE=$REMOTE"
  echo "BACKUP_REMOTE_KEEP_DAYS=90"
} >> .env
ok ".env yeniləndi: BACKUP_REMOTE=$REMOTE"

echo
echo "İlk yedək göndərilir…"
bash scripts/backup.sh 2>&1 | tail -6 | sed 's/^/  /'

echo
REMOTE_N=$(rclone ls "$REMOTE" 2>/dev/null | wc -l)
if [ "$REMOTE_N" -gt 0 ]; then
  printf "${G}Hazırdır${N} — kənarda %s fayl var.\n" "$REMOTE_N"
  echo "Bundan sonra hər gecəki yedək avtomatik ora gedəcək."
else
  printf "${Y}DİQQƏT${N} — kənarda fayl görünmür, yuxarıdakı çıxışa bax.\n"
fi
