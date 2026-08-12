"""Chunk vektorlarını hazırkı embedding modeli ilə yenidən hesablayır.

Model dəyişəndə MÜTLƏQ işlədilməlidir — fərqli modellərin vektorları
müqayisə oluna bilməz, qarışıq qalsa axtarış nəticələri mənasız olur.

Bərpa oluna bilir: hər chunk-da `embedding_model` saxlanılır, ona görə
proses kəsilsə təkrar işlədəndə yalnız qalan sətirlər emal olunur.

İstifadə (uzun sürdüyü üçün detached tövsiyə olunur):
    docker compose exec -d backend sh -c "python scripts/reembed.py > /tmp/reembed.log 2>&1"
    docker compose exec -T backend tail -3 /tmp/reembed.log
"""

import argparse
import sys
import time

sys.path.insert(0, "/app")

from sqlalchemy import func, or_, select                # noqa: E402
from sqlalchemy.orm import joinedload                   # noqa: E402
from app.config import settings                         # noqa: E402
from app.database import SessionLocal                   # noqa: E402
from app.models import Chunk                            # noqa: E402
from app.rag.chunker import embedding_signature, embedding_text  # noqa: E402
from app.rag.embedder import embed_texts                # noqa: E402

MODEL = embedding_signature(settings.embedding_model)
STALE = or_(Chunk.embedding_model.is_(None), Chunk.embedding_model != MODEL)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=128)
    args = ap.parse_args()

    db = SessionLocal()
    total = db.scalar(select(func.count(Chunk.id))) or 0
    todo = db.scalar(select(func.count(Chunk.id)).where(STALE)) or 0

    print(f"Model : {MODEL}")
    print(f"Chunk : {total} (köhnə vektorlu: {todo})", flush=True)
    if not todo:
        print("Hamısı artıq hazırkı modeldədir — ediləcək iş yoxdur.")
        return 0

    started = time.perf_counter()
    done = 0
    while True:
        rows = db.scalars(
            select(Chunk)
            .options(joinedload(Chunk.paper))
            .where(STALE)
            .order_by(Chunk.id)
            .limit(args.batch)
        ).all()
        if not rows:
            break

        # Ingest ilə EYNİ təmsil işlədilməlidir, yoxsa korpusda iki fərqli
        # vektor növü qarışar və oxşarlıq müqayisəsi mənasını itirər.
        vectors = embed_texts([embedding_text(r.paper.title, r.content) for r in rows])
        for row, vec in zip(rows, vectors):
            row.embedding = vec
            row.embedding_model = MODEL
        db.commit()

        done += len(rows)
        elapsed = time.perf_counter() - started
        rate = done / elapsed if elapsed else 0
        eta = (todo - done) / rate if rate else 0
        print(f"  {done}/{todo}  ({done * 100 // todo}%)  ~{eta / 60:.1f} dəq qalıb", flush=True)

    left = db.scalar(select(func.count(Chunk.id)).where(STALE)) or 0
    print(f"\nHazırdır: {done} chunk yeniləndi, {time.perf_counter() - started:.0f} saniyə")
    print(f"Qalan köhnə vektor: {left}")
    return 0 if left == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
