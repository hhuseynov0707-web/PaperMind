#!/usr/bin/env bash
# PaperMind — sistem doğrulaması. Codespace-də və ya serverdə bir əmrlə işləyir.
#
#   bash scripts/verify.sh
#
# Nə edir: stack-i qaldırır, sxemi yoxlayır, BÜTÜN testləri işlədir, intellekt
# qatının (çıxarış, əlaqələr, leksik indeks) hazır olub-olmadığına baxır, dedup
# korrektliyini real data ilə yoxlayır və retrieval baza xəttini ölçür.
#
# Heç nəyi silmir, heç nəyi dəyişmir — yalnız oxuyur və ölçür.

set -uo pipefail
cd "$(dirname "$0")/.."

BOLD=$'\e[1m'; RED=$'\e[31m'; GREEN=$'\e[32m'; YELLOW=$'\e[33m'; OFF=$'\e[0m'
FAILED=0

step()  { printf '\n%s▸ %s%s\n' "$BOLD" "$1" "$OFF"; }
ok()    { printf '  %s✓%s %s\n' "$GREEN" "$OFF" "$1"; }
warn()  { printf '  %s!%s %s\n' "$YELLOW" "$OFF" "$1"; }
fail()  { printf '  %s✗%s %s\n' "$RED" "$OFF" "$1"; FAILED=1; }

psql_q() { docker compose exec -T postgres psql -U elmradari -d elmradari -tAc "$1" 2>/dev/null; }

# ---------------------------------------------------------------- 1. stack
step "1/6 · Stack qaldırılır"
docker compose up -d --build >/tmp/pm-build.log 2>&1 \
  && ok "servislər işə düşdü" \
  || { fail "docker compose up uğursuz — /tmp/pm-build.log"; tail -20 /tmp/pm-build.log; exit 1; }

printf '  gözlənilir'
for i in $(seq 1 60); do
  if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    printf '\n'; ok "backend sağlamdır (${i}s)"; break
  fi
  printf '.'; sleep 2
  [ "$i" = 60 ] && { printf '\n'; fail "backend 120 saniyəyə qalxmadı"; docker compose logs --tail=30 backend; exit 1; }
done

# ------------------------------------------------------- 2. miqrasiya nəticəsi
step "2/6 · Miqrasiya (düzəldilmiş except bloku + yeni sütunlar)"
for col in pmid openalex_id; do
  got=$(psql_q "SELECT 1 FROM information_schema.columns WHERE table_name='papers' AND column_name='$col'")
  [ "$got" = "1" ] && ok "papers.$col mövcuddur" || fail "papers.$col YOXDUR — miqrasiya işləməyib"
done

# Bu blok əvvəllər `except`-in içində idi, yəni heç vaxt işləmirdi
orphan=$(psql_q "SELECT count(*) FROM papers WHERE source IS NULL")
[ "${orphan:-0}" = "0" ] && ok "source sütunu tam doldurulub" || warn "$orphan sətirdə source boşdur"

noprov=$(psql_q "SELECT count(*) FROM papers p WHERE NOT EXISTS (SELECT 1 FROM paper_sources s WHERE s.paper_id=p.id)")
[ "${noprov:-0}" = "0" ] && ok "hər məqalənin provenansı var" || warn "$noprov məqalədə provenans qeydi yoxdur"

# --------------------------------------------------------- 3. DOI unikallığı
step "3/6 · DOI unikallığı (D3)"
idx=$(psql_q "SELECT 1 FROM pg_indexes WHERE indexname='uq_papers_doi'")
dups=$(psql_q "SELECT count(*) FROM (SELECT doi FROM papers WHERE doi IS NOT NULL GROUP BY doi HAVING count(*)>1) t")
if [ "$idx" = "1" ]; then
  ok "unikal indeks qurulub — təkrar DOI mümkün deyil"
else
  warn "indeks qurulmayıb; bazada ${dups:-?} təkrar DOI qrupu var"
  [ "${dups:-0}" != "0" ] && psql_q "SELECT doi, count(*) FROM papers WHERE doi IS NOT NULL GROUP BY doi HAVING count(*)>1 LIMIT 5" | sed 's/^/      /'
fi

# ------------------------------------------------------------------ 4. testlər
step "4/6 · Test dəsti (DB testləri daxil)"
if docker compose exec -T backend python -m pytest tests/ -q --no-header 2>&1 | tee /tmp/pm-tests.log | tail -12; then
  ok "bütün testlər keçdi"
else
  fail "test uğursuzluğu — yuxarıdakı çıxışa bax"
fi

# ------------------------------------------------ 4b. Phase 4-6 cədvəlləri
step "4b/6 · İntellekt qatı (Phase 4-6)"
for t in paper_insights paper_relations; do
  got=$(psql_q "SELECT 1 FROM information_schema.tables WHERE table_name='$t'")
  [ "$got" = "1" ] && ok "$t cədvəli var" || fail "$t cədvəli YOXDUR — miqrasiya işləməyib"
done
ins=$(psql_q "SELECT count(*) FROM paper_insights")
rel=$(psql_q "SELECT count(*) FROM paper_relations")
total_p=$(psql_q "SELECT count(*) FROM papers")
printf '      çıxarış: %s / %s məqalə · əlaqə: %s\n' "${ins:-0}" "${total_p:-?}" "${rel:-0}"
if [ "${ins:-0}" = "0" ]; then
  warn "çıxarış yoxdur — landşaft və boşluq analizi boş qayıdacaq"
  warn "→ docker compose exec -d backend sh -c \"python scripts/extract_insights.py > /tmp/ins.log 2>&1\""
fi
# Leksik indeks (Phase 2) — hibrid axtarış üçün
for c in sv_en sv_ru; do
  got=$(psql_q "SELECT 1 FROM information_schema.columns WHERE table_name='papers' AND column_name='$c'")
  [ "$got" = "1" ] && ok "papers.$c (leksik indeks) var" || warn "papers.$c yoxdur — hibrid axtarış işləməz"
done

# ------------------------------------------------- 5. dedup real bazada
step "5/6 · Dedup korrektliyi (D1 real data üzərində)"
merged=$(psql_q "SELECT count(*) FROM (SELECT paper_id FROM paper_sources GROUP BY paper_id HAVING count(DISTINCT source)>1) t")
hist=$(psql_q "SELECT COALESCE(sum(merged),0) FROM ingest_runs")
if [ "${merged:-0}" != "0" ]; then
  ok "${merged} məqalə birdən çox mənbədə tapılıb (birləşdirilmiş)"
elif [ "${hist:-0}" != "0" ]; then
  warn "hazırda 0 çoxmənbəli məqalə var, amma tarixçədə ${hist} birləşmə qeyd olunub"
  warn "→ baza yenidən qurulub; dedup keçmişdə işləyib"
else
  warn "0 birləşmə — nə indi, nə tarixçədə. Dedup REAL SINAQDAN KEÇMƏYİB."
  warn "→ mənbələr üst-üstə düşməyən dəstlər çəkir; eyni sahə+dövr üzrə yoxla:"
  warn "  backfill_multi.py --sources arxiv,crossref --fields ai --days 30"
fi
psql_q "SELECT source, count(*) FROM papers GROUP BY source ORDER BY 2 DESC" | sed 's/|/: /;s/^/      /'

# D1: eyni başlıq + fərqli DOI = AYRI sətir olmalıdır
bad=$(psql_q "SELECT count(*) FROM papers a JOIN papers b ON a.title_key=b.title_key AND a.id<b.id WHERE a.doi IS NOT NULL AND b.doi IS NOT NULL AND a.doi=b.doi")
[ "${bad:-0}" = "0" ] && ok "eyni DOI-lu təkrar sətir yoxdur" || fail "${bad} təkrar aşkarlandı"

total=$(psql_q "SELECT count(*) FROM papers")
withdoi=$(psql_q "SELECT count(*) FROM papers WHERE doi IS NOT NULL")
ru=$(psql_q "SELECT count(*) FROM papers WHERE language='ru'")
printf '      korpus: %s məqalə · %s DOI-lu · %s rusdilli\n' "${total:-?}" "${withdoi:-?}" "${ru:-?}"

# --------------------------------------------------------------- 6. benchmark
step "6/6 · Retrieval baza xətti"
if [ "${total:-0}" -lt 100 ]; then
  warn "korpus çox kiçikdir (${total:-0}) — benchmark mənalı deyil"
  warn "əvvəlcə: docker compose exec backend python scripts/backfill_multi.py --days 14 --limit 80"
else
  # tail YOX: kəsilmiş çıxış blokların başlığını itirir və rejimləri qarışdırır
  # (bir dəfə "ORİJİNAL + TƏRCÜMƏ" bloku produksiya siyasəti kimi oxunmuşdu).
  docker compose exec -T backend python scripts/benchmark.py --compare 2>&1 | tee /tmp/pm-bench.log
  ok "nəticə /tmp/pm-bench.log faylındadır"
fi

# ------------------------------------------------------------------ yekun
printf '\n%s' "$BOLD"
if [ "$FAILED" = "0" ]; then
  printf '%s✓ Sistem doğrulandı%s\n' "$GREEN" "$OFF"
else
  printf '%s✗ Problemlər var — yuxarıya bax%s\n' "$RED" "$OFF"
fi
printf 'Loglar: /tmp/pm-tests.log · /tmp/pm-bench.log\n'
exit "$FAILED"
