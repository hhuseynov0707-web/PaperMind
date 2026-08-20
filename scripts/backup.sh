#!/usr/bin/env bash
# Bazanın gündəlik ŞİFRƏLƏNMİŞ ehtiyat nüsxəsi.
#
#   0 3 * * * cd ~/papermind && bash scripts/backup.sh >> ~/backup.log 2>&1
#
# ## Niyə şifrələnir
#
# Dump-un içində `users` (e-poçt + argon2 həşləri), `billing_events`
# (ödəniş qeydləri), `user_sessions`, `documents` və istifadəçi sualları var.
# Yəni bu fayl bazanın özü qədər həssasdır. Şifrələnməmiş halda serverdə
# durması, onu ələ keçirən adama hər şeyi bir faylda təqdim etmək deməkdir.
#
# ## Niyə ASİMMETRİK (parol yox, açar cütü)
#
# Parolla şifrələsəydik, parol serverdə — `.env`-də — durmalı idi. Serveri
# ələ keçirən adam həm yedəyi, həm parolu alardı; şifrələmə heç nə qazandırmazdı.
#
# Burada server yalnız AÇIQ açarı daşıyır. Onunla şifrələmək olar, açmaq OLMAZ.
# Gizli açar heç vaxt serverə düşmür. Nəticə: server tam ələ keçsə belə,
# nə serverdəki, nə də kənardakı yedəklər açıla bilmir.
#
# ## BUNU İTİRMƏ
#
# Gizli açar itsə, yedəklər ƏBƏDİ bağlanır. Bərpa yolu yoxdur — dizayn belədir.
# Açar `papermind-keys/backup-PRIVATE.asc` faylındadır; onu bu kompüterdən
# kənarda da saxla (parol meneceri, ayrıca disk).
#
# ## Açıq nüsxə saxlanılmır
#
# Şifrələnmə bitən kimi `.sql.gz` silinir. Sürətli bərpa üçün açıq nüsxə
# saxlamaq rahat olardı, amma o, bütün müdafiəni mənasız edir.

set -euo pipefail
cd "$(dirname "$0")/.."

DIR="${BACKUP_DIR:-$HOME/papermind-backups}"
KEEP="${BACKUP_KEEP:-14}"
RECIPIENT="${BACKUP_GPG_RECIPIENT:-727290D1A0D4381544FDF0A965C3378C2388B62F}"
COMPOSE="docker compose -f docker-compose.prod.yml"
[ -f docker-compose.prod.yml ] || COMPOSE="docker compose"

mkdir -p "$DIR"
STAMP="$(date +%F-%H%M)"
RAW="$DIR/papermind-$STAMP.sql.gz"
ENC="$RAW.gpg"

set -a; [ -f .env ] && . ./.env; set +a
USER_DB="${POSTGRES_USER:-elmradari}"
NAME_DB="${POSTGRES_DB:-elmradari}"

# Açar olmadan davam etmirik. Əks halda skript «uğurla» işləyib şifrələnməmiş
# nüsxə buraxardı və bunu heç kim görməzdi.
if ! gpg --list-keys "$RECIPIENT" >/dev/null 2>&1; then
  echo "XƏTA: GPG açığı açarı tapılmadı ($RECIPIENT)"
  echo "  Quraşdır:  gpg --import backup-public.asc"
  exit 1
fi

echo "[$(date '+%F %T')] backup başlayır -> $(basename "$ENC")"
$COMPOSE exec -T postgres pg_dump -U "$USER_DB" "$NAME_DB" | gzip > "$RAW"

if [ ! -s "$RAW" ]; then
  echo "XƏTA: dump boşdur, silinir"
  rm -f "$RAW"
  exit 1
fi
RAW_SIZE=$(du -h "$RAW" | cut -f1)

# `--trust-model always`: açar bizim özümüzün yaratdığımızdır, imza zənciri yoxdur.
gpg --batch --yes --trust-model always \
    --recipient "$RECIPIENT" --output "$ENC" --encrypt "$RAW"

if [ ! -s "$ENC" ]; then
  echo "XƏTA: şifrələmə alınmadı — açıq nüsxə silinir, yedək YOXDUR"
  rm -f "$RAW" "$ENC"
  exit 1
fi

# Fayl həqiqətən PGP mesajıdırmı və BİZİM açara şifrələnibmi?
#
# `gpg --list-packets` çıxış KODUNA baxmaq olmaz: o, faylı açmağa da cəhd
# edir və gizli açar burada olmadığı üçün həmişə sıfırdan fərqli kod qaytarır.
# Yəni belə yoxlama məhz onu işlədəcək maşında heç vaxt keçə bilməzdi.
#
# Ona görə çıxışın MƏZMUNU oxunur. Bu, iki şeyi birdən təsdiqləyir:
# fayl düzgün OpenPGP mesajıdır və düzgün açara şifrələnib — yanlış
# alıcı təyin olunsa, yedək «uğurlu» görünüb açıla bilməz olardı.
KEYID="${RECIPIENT: -16}"
PACKETS=$(gpg --list-packets "$ENC" 2>&1 || true)
if ! echo "$PACKETS" | grep -qi "pubkey enc packet"; then
  echo "XƏTA: nəticə OpenPGP mesajı deyil"
  rm -f "$RAW" "$ENC"; exit 1
fi
if ! echo "$PACKETS" | grep -qi "keyid $KEYID"; then
  echo "XƏTA: yanlış açara şifrələnib (gözlənilən keyid: $KEYID)"
  rm -f "$RAW" "$ENC"; exit 1
fi

rm -f "$RAW"                       # açıq nüsxə serverdə QALMIR
echo "[$(date '+%F %T')] hazırdır ($RAW_SIZE -> $(du -h "$ENC" | cut -f1), şifrələnmiş)"

# Köhnə nüsxələr
ls -1t "$DIR"/papermind-*.sql.gz.gpg 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r old; do
  rm -f "$old"
  echo "  silindi: $(basename "$old")"
done
# Keçid dövründən qalan şifrələnməmiş nüsxələr ÇEVRİLİR, silinmir.
#
# Əvvəlki versiya onları sadəcə silirdi və bu, yanlış idi: şifrələməyə keçid
# yedək TARİXÇƏSİNİ məhv etməməlidir. Şifrələnməmiş fayl problemdir, amma
# həlli onu şifrələməkdir — yox etmək yox. Yalnız çevrilmə uğursuz olsa
# fayl yerində qalır ki, əl ilə baxmaq mümkün olsun.
ls -1 "$DIR"/papermind-*.sql.gz 2>/dev/null | while read -r plain; do
  target="$plain.gpg"
  if [ -f "$target" ]; then
    rm -f "$plain"
    echo "  artıq şifrələnib, açıq nüsxə silindi: $(basename "$plain")"
  elif gpg --batch --yes --trust-model always          --recipient "$RECIPIENT" --output "$target" --encrypt "$plain" 2>/dev/null        && [ -s "$target" ]; then
    rm -f "$plain"
    echo "  şifrələndi: $(basename "$target")"
  else
    echo "  DİQQƏT: çevrilmədi, olduğu kimi qalır: $(basename "$plain")"
  fi
done

echo "  saxlanılan: $(ls -1 "$DIR"/papermind-*.sql.gz.gpg 2>/dev/null | wc -l) şifrələnmiş nüsxə"

# --- Kənar surət ----------------------------------------------------------
# rclone konfiqurasiya olunubsa, yeni nüsxə dərhal kənara göndərilir.
# Olmasa, xəbərdarlıq verilir — SƏSSİZ keçmir, çünki «kənar yedək var»
# zənni ilə yaşamaq, heç olmamasından pisdir.
if command -v rclone >/dev/null 2>&1 && [ -n "${BACKUP_REMOTE:-}" ]; then
  if rclone copy "$ENC" "$BACKUP_REMOTE" --no-traverse 2>&1 | sed 's/^/  rclone: /'; then
    echo "  kənara göndərildi: $BACKUP_REMOTE"
    # Kənarda da köhnələri təmizlə
    rclone delete "$BACKUP_REMOTE" --min-age "${BACKUP_REMOTE_KEEP_DAYS:-90}d" 2>/dev/null || true
  else
    echo "  DİQQƏT: kənara göndərmə alınmadı"
  fi
else
  echo "  DİQQƏT: kənar surət qurulmayıb (BACKUP_REMOTE boşdur)."
  echo "           Yedəklər YALNIZ bu serverdədir — server itsə, onlar da itir."
fi
