"""Məqalələr arası əlaqələri qurur — §15.

Üç mənbədən, üç fərqli etibarlılıqla:

  1. SİTATLAR (fakt) — OpenAlex `referenced_works`. Yalnız hər iki tərəf
     korpusda olanda əlaqə yaranır: bizdə olmayan məqaləyə istinad saxlamaq
     mənasızdır, çünki istifadəçi ona keçə bilmir.
  2. ORTAQ MÜƏLLİF (hesablanmış) — soyad kəsişməsi.
  3. OXŞARLIQ (ölçülmüş) — vektor yaxınlığı, həddən yuxarı olanlar.

Bərpa olunandır: mövcud əlaqələr `ON CONFLICT DO NOTHING` ilə keçilir.

    docker compose exec backend python scripts/build_relations.py
    docker compose exec backend python scripts/build_relations.py --skip-citations
"""

import argparse
import sys
import time

sys.path.insert(0, "/app")

from sqlalchemy import func, select                     # noqa: E402
from sqlalchemy.dialects.postgresql import insert       # noqa: E402
from sqlalchemy.orm import selectinload                 # noqa: E402

from app.database import SessionLocal                   # noqa: E402
from app.models import Paper, PaperRelation             # noqa: E402
from app.relations import (                             # noqa: E402
    RELATED_MAX_PER_PAPER,
    RELATED_MIN_SCORE,
    author_keys,
    author_overlap,
    build_relation,
    classify_citation_direction,
    normalize_openalex_refs,
)
from app.sources.common import get_with_retry            # noqa: E402
from app.sources.openalex import _headers                  # noqa: E402

OPENALEX_API = "https://api.openalex.org/works"

# Çox yayılmış ad yüzlərlə məqaləni bir-birinə bağlayır və bu, əlaqə deyil,
# ad təsadüfüdür. Qruplaşdırma açarı «baş hərf + soyad»dır (yalnız soyad
# deyil) — ilk icra 5 551 əlaqə verdi, çünki «wang» tək açar idi.
MAX_GROUP_PER_KEY = 25


def save(db, rows: list[dict]) -> int:
    """Əlaqələri yazır, təkrarları keçir."""
    rows = [r for r in rows if r]
    if not rows:
        return 0
    stmt = insert(PaperRelation).values(rows).on_conflict_do_nothing(
        constraint="uq_relation"
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0


def build_citations(db, limit: int) -> int:
    """OpenAlex referenced_works → `cites` / `builds_on`."""
    papers = db.scalars(
        select(Paper).where(Paper.openalex_id.is_not(None)).order_by(Paper.id).limit(limit)
    ).all()
    if not papers:
        print("  OpenAlex ID-si olan məqalə yoxdur — sitat qurula bilməz.")
        print("  Qeyd: OpenAlex ID yalnız openalex mənbəsindən gələn qeydlərdə var.")
        return 0

    # Korpusdakı bütün OpenAlex ID-ləri: yalnız HƏR İKİ tərəfi bizdə olan
    # sitatlar saxlanılır
    known = dict(
        db.execute(
            select(Paper.openalex_id, Paper.id).where(Paper.openalex_id.is_not(None))
        ).all()
    )
    print(f"  OpenAlex ID-li məqalə: {len(known)} · sorğu ediləcək: {len(papers)}")

    made = 0
    for i, paper in enumerate(papers, start=1):
        try:
            resp = get_with_retry(
                f"{OPENALEX_API}/{paper.openalex_id}",
                params={"select": "id,referenced_works,publication_year"},
                headers=_headers(), timeout=30,
            )
            work = resp.json() or {}
        except Exception as exc:
            print(f"  [{i}/{len(papers)}] {paper.openalex_id}: {str(exc)[:60]}")
            continue

        from_year = work.get("publication_year")
        rows = []
        for ref in normalize_openalex_refs(work.get("referenced_works")):
            target = known.get(ref)
            if not target:
                continue                      # bizdə yoxdur — keçidsiz əlaqə mənasızdır
            to_paper = db.get(Paper, target)
            to_year = to_paper.published_at.year if to_paper and to_paper.published_at else None
            rows.append(build_relation(
                paper.id, target,
                classify_citation_direction(from_year, to_year),
                source="openalex",
                evidence=f"OpenAlex referenced_works: {ref}",
            ))
        made += save(db, rows)
        if i % 20 == 0:
            print(f"  [{i}/{len(papers)}] əlaqə: {made}", flush=True)
        time.sleep(0.2)                        # OpenAlex nəzakət limiti
    return made


def build_author_links(db) -> int:
    """Ortaq müəllifi olan məqalələr — `same_authors`."""
    papers = db.scalars(
        select(Paper).options(selectinload(Paper.authors)).order_by(Paper.id)
    ).all()

    by_key: dict[str, list] = {}
    for p in papers:
        for k in author_keys([a.name for a in p.authors]):
            by_key.setdefault(k, []).append(p)

    rows, seen = [], set()
    for group in by_key.values():
        if len(group) < 2 or len(group) > MAX_GROUP_PER_KEY:
            continue
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                key = (min(a.id, b.id), max(a.id, b.id))
                if key in seen:
                    continue
                seen.add(key)
                shared = author_overlap(
                    [x.name for x in a.authors], [x.name for x in b.authors]
                )
                # Kəsişmə boşdursa əlaqə YAZILMIR. İlk versiya bunu yoxlamırdı
                # və qrupa düşən hər cüt üçün sətir yaradırdı — hətta baş hərf
                # uyğun gəlməsə belə.
                if not shared:
                    continue
                rows.append(build_relation(
                    key[0], key[1], "same_authors", source="authors",
                    evidence="ortaq müəllif: " + ", ".join(sorted(shared)[:5]),
                ))
    return save(db, rows)


def build_similarity_links(db, limit: int) -> int:
    """Vektor oxşarlığı ilə `related_to`."""
    from app.rag.retriever import vector_search

    papers = db.scalars(select(Paper).order_by(Paper.id).limit(limit)).all()
    made = 0
    for i, paper in enumerate(papers, start=1):
        hits = vector_search(db, paper.title, RELATED_MAX_PER_PAPER + 1)
        rows = []
        for h in hits:
            if h["paper_id"] == paper.id or h["score"] < RELATED_MIN_SCORE:
                continue
            rows.append(build_relation(
                paper.id, h["paper_id"], "related_to", source="similarity",
                confidence=round(h["score"], 3),
                evidence=f"vektor oxşarlığı {h['score']:.2f}",
            ))
        made += save(db, rows)
        if i % 100 == 0:
            print(f"  [{i}/{len(papers)}] əlaqə: {made}", flush=True)
    return made


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=400, help="sitat üçün neçə məqalə sorğulansın")
    ap.add_argument("--similarity-limit", type=int, default=600)
    ap.add_argument("--skip-citations", action="store_true")
    ap.add_argument("--skip-similarity", action="store_true")
    args = ap.parse_args()

    db = SessionLocal()
    before = db.scalar(select(func.count(PaperRelation.id))) or 0
    print(f"Mövcud əlaqə: {before}\n")

    if not args.skip_citations:
        print("1/3 · Sitatlar (OpenAlex referenced_works)")
        print(f"  yeni: {build_citations(db, args.limit)}\n")

    print("2/3 · Ortaq müəlliflər")
    print(f"  yeni: {build_author_links(db)}\n")

    if not args.skip_similarity:
        print("3/3 · Vektor oxşarlığı")
        print(f"  yeni: {build_similarity_links(db, args.similarity_limit)}\n")

    after = db.scalar(select(func.count(PaperRelation.id))) or 0
    print("=" * 50)
    print(f"  cəmi əlaqə: {before} → {after}  (+{after - before})")
    for rel, n in db.execute(
        select(PaperRelation.relation, func.count())
        .group_by(PaperRelation.relation).order_by(func.count().desc())
    ).all():
        print(f"    {rel:<14} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
