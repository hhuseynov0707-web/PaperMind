"""Məqalələrdən strukturlu çıxarış — §7.

Bu, Phase 4-ün təməlidir: müqayisə (§9), ziddiyyət (§10), landşaft (§11) və
boşluqlar (§13) hamısı çıxarışın üzərində işləyir.

Bərpa olunandır: hər məqalə üçün model imzası saxlanılır, kəsilsə qaldığı
yerdən davam edir. Groq pulsuz qatında dəqiqəlik limit olduğuna görə
sorğular arasında fasilə var və 429-da gözləyib təkrar cəhd edilir.

    docker compose exec backend python scripts/extract_insights.py --limit 50
    docker compose exec -d backend sh -c "python scripts/extract_insights.py > /tmp/ins.log 2>&1"
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, "/app")

from sqlalchemy import func, or_, select                # noqa: E402
from app.config import settings                        # noqa: E402
from app.database import SessionLocal                  # noqa: E402
from app.models import Paper, PaperInsight             # noqa: E402
from app.rag.insights import (                         # noqa: E402
    evidence_summary,
    extract_insight,
    insight_model_tag,
)

TAG = insight_model_tag()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0 = hamısı")
    ap.add_argument("--delay", type=float, default=2.5, help="sorğular arası fasilə (san)")
    ap.add_argument("--field", type=str, default=None, help="yalnız bu sahə")
    args = ap.parse_args()

    if not settings.groq_api_key:
        print("GROQ_API_KEY yoxdur.")
        return 1

    db = SessionLocal()

    # Çıxarışı olmayan VƏ ya köhnə imzalı məqalələr
    done_ids = select(PaperInsight.paper_id).where(PaperInsight.model == TAG)
    stmt = select(Paper).where(Paper.id.not_in(done_ids)).order_by(Paper.id)
    if args.field:
        stmt = stmt.where(Paper.field_keys.any(args.field))
    if args.limit:
        stmt = stmt.limit(args.limit)

    todo = db.scalars(stmt).all()
    total_papers = db.scalar(select(func.count(Paper.id))) or 0
    have = db.scalar(
        select(func.count(PaperInsight.paper_id)).where(PaperInsight.model == TAG)
    ) or 0

    print(f"Model  : {TAG}")
    print(f"Korpus : {total_papers} məqalə · hazır çıxarış: {have}")
    print(f"İşlənəcək: {len(todo)}\n", flush=True)
    if not todo:
        print("Ediləcək iş yoxdur.")
        return 0

    started = time.perf_counter()
    ok = failed = 0
    for i, paper in enumerate(todo, start=1):
        try:
            data = extract_insight(paper.title, paper.abstract)
        except Exception as exc:
            msg = str(exc)
            if "429" in msg or "rate limit" in msg.lower():
                print(f"  [{i}/{len(todo)}] limit — 20 san gözlənilir", flush=True)
                time.sleep(20)
                try:
                    data = extract_insight(paper.title, paper.abstract)
                except Exception as exc2:
                    print(f"  [{i}/{len(todo)}] XƏTA: {str(exc2)[:70]}", flush=True)
                    failed += 1
                    continue
            else:
                print(f"  [{i}/{len(todo)}] XƏTA: {msg[:70]}", flush=True)
                failed += 1
                continue

        row = db.get(PaperInsight, paper.id)
        if row is None:
            row = PaperInsight(paper_id=paper.id)
            db.add(row)
        row.data = data
        row.model = TAG
        db.commit()
        ok += 1

        ev = evidence_summary(data)
        if i % 5 == 0 or i == len(todo):
            rate = i / (time.perf_counter() - started)
            left = (len(todo) - i) / rate if rate else 0
            print(
                f"  [{i}/{len(todo)}] {ev['fields_extracted']}/{ev['fields_possible']} sahə "
                f"(stated {ev['stated']}, sintez {ev['synthesized']}, nəticə {ev['inferred']}) "
                f"· qalan ~{left/60:.0f} dəq",
                flush=True,
            )
        time.sleep(args.delay)

    print(f"\nHazır: {ok} · uğursuz: {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
