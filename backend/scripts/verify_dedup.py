"""Çarpaz mənbə birləşməsinin REAL data ilə yoxlanması.

Niyə lazımdır: auditdə "provenanslı kimlik sxemi yaxşıdır" (G1) yazılmışdı,
amma canlı bazada `sum(ingest_runs.merged) = 0` çıxdı — yəni mexanizm 10 yığım
ərzində bir dəfə də işə düşməyib. Vahid testlər onu sintetik data ilə sübut edir;
bu skript isə REAL mənbələrlə sübut və ya təkzib edir.

Necə işləyir:
  1. Bazadan DOAJ-dan gələn, DOI-su olan məqalələr seçilir
  2. Həmin DOI-lar Crossref API-dən BİRBAŞA çəkilir (eyni iş, başqa mənbə)
  3. upsert_papers() ilə yığılır
  4. Nəticə yoxlanılır: yeni sətir yaranmamalı, provenans 2 mənbəyə çatmalıdır

Bu, dedup-un ən sərt yoxlamasıdır: identifikator eynidir, ona görə birləşmə
BAŞ VERMƏLİDİR. Baş verməzsə, kodda problem var və onu tapmalıyıq.

    docker compose exec backend python scripts/verify_dedup.py --limit 15
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select                       # noqa: E402
from sqlalchemy.orm import Session                        # noqa: E402

from app.crud import upsert_papers                        # noqa: E402
from app.database import engine                           # noqa: E402
from app.models import Paper, PaperSource                 # noqa: E402
from app.schemas import PaperIn                           # noqa: E402
from app.sources.common import get_with_retry             # noqa: E402
from app.sources.crossref import API, _headers, _parse    # noqa: E402


def fetch_by_doi(doi: str, field_key: str) -> dict | None:
    """Crossref-dən konkret DOI-nu çəkir (axtarış yox, birbaşa müraciət)."""
    try:
        resp = get_with_retry(f"{API}/{doi}", headers=_headers(), timeout=30)
        message = (resp.json() or {}).get("message")
    except Exception as exc:
        print(f"    ! {doi}: {str(exc)[:80]}")
        return None
    return _parse(message, field_key) if message else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=15, help="neçə DOI sınansın")
    args = ap.parse_args()

    with Session(engine) as db:
        before_papers = db.scalar(select(func.count()).select_from(Paper))
        before_sources = db.scalar(select(func.count()).select_from(PaperSource))

        rows = db.scalars(
            select(Paper)
            .where(Paper.source == "doaj", Paper.doi.is_not(None))
            .order_by(Paper.id)
            .limit(args.limit)
        ).all()

        if not rows:
            print("DOAJ-dan DOI-lu məqalə tapılmadı — əvvəlcə backfill lazımdır.")
            return 1

        print(f"Baza: {before_papers} məqalə, {before_sources} provenans sətri")
        print(f"Sınaq: {len(rows)} DOAJ DOI-su Crossref-dən çəkilir\n")

        targets = {p.doi: (p.id, p.field_keys[0] if p.field_keys else "ai") for p in rows}

        incoming: list[PaperIn] = []
        for doi, (_, field_key) in targets.items():
            parsed = fetch_by_doi(doi, field_key)
            if parsed:
                incoming.append(PaperIn(**parsed))
                print(f"    ✓ Crossref-də tapıldı: {doi}")
            else:
                print(f"    – Crossref-də yoxdur:   {doi}")

        if not incoming:
            print("\nCrossref heç birini tanımadı — sınaq nəticəsizdir.")
            return 1

        print(f"\n{len(incoming)} qeyd yığılır…")
        inserted, skipped, merged = upsert_papers(db, incoming)

        after_papers = db.scalar(select(func.count()).select_from(Paper))
        after_sources = db.scalar(select(func.count()).select_from(PaperSource))

        print("\n" + "=" * 56)
        print(f"  inserted={inserted}  skipped={skipped}  merged={merged}")
        print(f"  məqalə sayı:  {before_papers} → {after_papers}  (+{after_papers - before_papers})")
        print(f"  provenans:    {before_sources} → {after_sources}  (+{after_sources - before_sources})")

        multi = db.execute(
            select(PaperSource.paper_id)
            .where(PaperSource.paper_id.in_([pid for pid, _ in targets.values()]))
            .group_by(PaperSource.paper_id)
            .having(func.count(func.distinct(PaperSource.source)) > 1)
        ).all()

        print(f"  indi çoxmənbəli: {len(multi)} / {len(targets)}")
        print("=" * 56)

        ok = inserted == 0 and len(multi) > 0
        if ok:
            print("\n✓ DEDUP İŞLƏYİR: yeni sətir yaranmadı, provenans genişləndi.")
        elif inserted > 0:
            print(f"\n✗ PROBLEM: {inserted} YENİ sətir yarandı — eyni DOI dublikat oldu.")
        else:
            print("\n! Qeydlər tanındı, amma provenans genişlənmədi.")
            print("  Ehtimal: Crossref eyni external_id-ni qaytarır və mənbə fərqi yazılmır.")
        return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
