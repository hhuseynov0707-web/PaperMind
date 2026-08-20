#!/usr/bin/env bash
# PaperMind — lokal maşından tam deploy zənciri.
#
#   bash scripts/ship.sh                    # təmiz ağac tələb edir
#   bash scripts/ship.sh -m "feat: ..."     # əvvəlcə hər şeyi commit edir
#   bash scripts/ship.sh --no-test          # testləri atlayır (tövsiyə olunmur)
#   bash scripts/ship.sh --dry-run          # push və deploy etmir, yalnız yoxlayır
#
# `scripts/deploy.sh` SERVERDƏ işləyir; bu isə lokalda işləyir və onu çağırır.
#
# Əsas prinsip: hər addım NƏTİCƏNİ ölçür, «xəta vermədi»ni yox. Deploy-un
# uğurlu görünüb serverdə köhnə kodun qalması bu layihədə artıq baş verib.
set -uo pipefail

HOST="${PM_HOST:-root@2.28.22.89}"
KEY="${PM_KEY:-$HOME/.ssh/papermind}"
REMOTE_DIR="${PM_DIR:-/root/papermind}"
SITE="${PM_SITE:-https://papermind.duckdns.org}"

G='\033[32m'; R='\033[31m'; Y='\033[33m'; C='\033[36m'; N='\033[0m'
ok()   { printf "  ${G}OK${N}    %s\n" "$1"; }
bad()  { printf "  ${R}XƏTA${N}  %s\n" "$1"; FAIL=$((FAIL+1)); }
warn() { printf "  ${Y}DİQQƏT${N} %s\n" "$1"; }
step() { printf "\n${C}==> %s${N}\n" "$1"; }
FAIL=0

MSG=""; RUN_TESTS=yes; DRY=no
while [ $# -gt 0 ]; do
  case "$1" in
    -m|--message) MSG="${2:-}"; shift 2 ;;
    --no-test)    RUN_TESTS=no; shift ;;
    --dry-run|-n) DRY=yes; shift ;;
    -h|--help)    sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "naməlum arqument: $1"; exit 1 ;;
  esac
done

cd "$(dirname "$0")/.." || exit 1
ROOT=$(pwd)

# ---------------------------------------------------------------- 1. lokal
step "1/6 · Lokal vəziyyət"

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { bad "git repo deyil"; exit 1; }
BRANCH=$(git rev-parse --abbrev-ref HEAD)
ok "branch: $BRANCH"

DIRTY=$(git status --porcelain | wc -l)
if [ "$DIRTY" -gt 0 ]; then
  if [ -z "$MSG" ]; then
    bad "$DIRTY fayl commit olunmayıb"
    echo
    git status --short
    echo
    echo "  Commit mesajı ver:  bash scripts/ship.sh -m \"feat: ...\""
    exit 1
  fi
  ok "$DIRTY fayl commit ediləcək"
else
  ok "işçi ağac təmizdir"
fi

# Sirr yoxlaması commit-dən ƏVVƏL. Bir dəfə push olunan açar geri qaytarıla
# bilməz — yalnız ləğv edilə bilər, ona görə bu addım dayandırıcıdır.
#
# Naxış SİRR FAYLLARINI tutur, adında «backup» keçən skriptləri yox. Əvvəlki
# variantda sadəcə `backup` sözü vardı və `scripts/backup.sh`-ı da işarələyirdi.
# Yalançı həyəcan verən qoruyucu bir müddət sonra tamamilə nəzərə alınmır —
# yəni belə naxış qorumanı gücləndirmir, zəiflədir.
SECRETS=$(git status --porcelain | awk '{print $NF}' \
          | grep -ivE '[.](sh|md|py|js|yml|yaml)$' \
          | grep -iE '(^|/)[.]env($|[.])|[.](key|pem|asc|gpg|p12|pfx|jks)$|[.]sql([.]gz)?$|[.](dump|bak)$|id_(rsa|ed25519)$' || true)
if [ -n "$SECRETS" ]; then
  bad "sirr ola bilən fayllar:"
  echo "$SECRETS" | sed 's/^/      /'
  echo "      .gitignore-a əlavə et, sonra təkrar işlət."
  exit 1
fi
ok "sirr aşkarlanmadı"

# ---------------------------------------------------------------- 2. testlər
step "2/6 · Testlər"
if [ "$RUN_TESTS" = yes ]; then
  if (cd backend && python -m pytest tests/ -q >/tmp/pm-test.log 2>&1); then
    ok "$(tail -1 /tmp/pm-test.log | tr -d '\r')"
  else
    bad "testlər düşdü"
    tail -25 /tmp/pm-test.log | sed 's/^/      /'
    exit 1
  fi
else
  warn "testlər atlandı (--no-test)"
fi

# ---------------------------------------------------- 3. asset versiyası
# Bu yoxlama real problemdən doğub: statik fayl dəyişib, `?v=` isə qalıb —
# brauzer köhnə JS-i keşdən verir və dəyişiklik «tətbiq olunmadı» görünür.
step "3/6 · Asset versiyası"
STATIC_CHANGED=$( { git diff --name-only; git diff --cached --name-only; git ls-files -o --exclude-standard; } \
                  | grep -c 'backend/app/static/' || true)
CUR_V=$(grep -oE '\?v=[0-9.]+' backend/app/static/index.html | head -1)
if [ "$STATIC_CHANGED" -gt 0 ]; then
  PREV_V=$(git show HEAD:backend/app/static/index.html 2>/dev/null \
           | grep -oE '\?v=[0-9.]+' | head -1)
  if [ "$CUR_V" = "$PREV_V" ]; then
    bad "statik fayl dəyişib, amma versiya $CUR_V olaraq qalıb"
    echo "      Brauzer köhnə faylı keşdən verəcək. index.html-də ?v= artır:"
    echo "      sed -i 's/?v=${CUR_V#?v=}/?v=YENİ/g' backend/app/static/index.html"
    exit 1
  fi
  ok "versiya artırılıb: $PREV_V -> $CUR_V"
else
  ok "statik fayl dəyişməyib ($CUR_V)"
fi

# ---------------------------------------------------------- 4. commit/push
step "4/6 · Commit və push"
if [ "$DRY" = yes ]; then
  warn "quru rejim — commit/push edilmir"
  LOCAL_SHA=$(git rev-parse HEAD)
elif [ "$DIRTY" -gt 0 ]; then
  git add -A
  git commit -q -m "$MSG" || { bad "commit alınmadı"; exit 1; }
  ok "commit: $(git log -1 --format='%h %s')"
fi

LOCAL_SHA=$(git rev-parse HEAD)
if [ "$DRY" = yes ]; then
  :
elif git push -q origin "$BRANCH" 2>/tmp/pm-push.log; then
  ok "push: ${LOCAL_SHA:0:7} -> origin/$BRANCH"
else
  bad "push alınmadı"; sed 's/^/      /' /tmp/pm-push.log; exit 1
fi
[ "$DRY" = yes ] && ok "commit ${LOCAL_SHA:0:7} (push atlandı)"

# ------------------------------------------------------------- 5. server
step "5/6 · Serverdə deploy"
SSH="ssh -o ConnectTimeout=15 -i $KEY $HOST"

if ! $SSH true 2>/dev/null; then
  bad "serverə qoşulmaq alınmadı ($HOST)"
  echo "      Şəbəkə SSH-i bloklayırsa: Hetzner konsolunda tək sətir işlət —"
  echo "      cd $REMOTE_DIR; git pull; bash scripts/deploy.sh"
  exit 1
fi
ok "qoşuldu"

if [ "$DRY" = yes ]; then
  warn "quru rejim — deploy.sh işlədilmir"
else
  $SSH "cd $REMOTE_DIR && git fetch -q origin && git reset -q --hard origin/$BRANCH && bash scripts/deploy.sh"
  DEPLOY_RC=$?
  [ $DEPLOY_RC -eq 0 ] && ok "deploy.sh tamamlandı" || bad "deploy.sh kod $DEPLOY_RC ilə bitdi"
fi

# ------------------------------------------------------------ 6. yoxlama
# Ən vacib addım. deploy.sh «OK» deyə bilər, amma bu, PUSH ETDİYİM kodun
# işlədiyini sübut etmir — konteyner köhnə image-lə də qalxa bilər.
step "6/6 · Nəticənin yoxlanması"

REMOTE_SHA=$($SSH "cd $REMOTE_DIR && git rev-parse HEAD" 2>/dev/null | tr -d '\r')
if [ "$REMOTE_SHA" = "$LOCAL_SHA" ]; then
  ok "server eyni commit-dədir (${REMOTE_SHA:0:7})"
else
  bad "commit uyğunsuzluğu — lokal ${LOCAL_SHA:0:7}, server ${REMOTE_SHA:0:7}"
fi

RUNNING=$($SSH "cd $REMOTE_DIR && docker compose -f docker-compose.prod.yml ps --format '{{.Service}}:{{.State}}'" 2>/dev/null | tr -d '\r' | tr '\n' ' ')
case "$RUNNING" in
  *backend:running*) ok "konteynerlər: $RUNNING" ;;
  *) bad "backend işləmir: $RUNNING" ;;
esac

CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$SITE/health")
[ "$CODE" = "200" ] && ok "sağlamlıq: 200" || bad "sağlamlıq: $CODE"

# Brauzerin görəcəyi HTML həqiqətən yeni versiyadırmı? Caddy və ya brauzer
# keşi burada üzə çıxır.
LIVE_V=$(curl -s --max-time 20 "$SITE/" | grep -oE '\?v=[0-9.]+' | head -1)
if [ "$LIVE_V" = "$CUR_V" ]; then
  ok "canlı asset versiyası: $LIVE_V"
else
  bad "canlı versiya $LIVE_V, gözlənilən $CUR_V"
fi

echo
echo "======================================"
if [ "$FAIL" -eq 0 ]; then
  printf "Nəticə: ${G}hamısı OK${N}\n\n%s\n" "$SITE"
else
  printf "Nəticə: ${R}%s xəta${N}\n" "$FAIL"
  echo
  echo "Loglara bax:"
  echo "  ssh -i $KEY $HOST 'cd $REMOTE_DIR && docker compose -f docker-compose.prod.yml logs --tail 60 backend'"
fi
exit "$FAIL"
