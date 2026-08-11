from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import cache, crud
from ..database import get_db
from ..fields import FIELDS
from ..schemas import IngestBatch, IngestResult, PaperIn, PullRequest, PullResult
from ..security import require_admin_key
from ..sources import SOURCES

# Yazma endpoint-ləri: ictimai rejimdə X-API-Key tələb olunur
router = APIRouter(prefix="/api", tags=["ingest"], dependencies=[Depends(require_admin_key)])


@router.post("/ingest", response_model=IngestResult, status_code=201)
def ingest(batch: IngestBatch, db: Session = Depends(get_db)):
    """Hazır batch qəbul edir (n8n W1 və backfill skripti bunu işlədir).

    Məqalələr deduplikasiya olunur: eyni iş başqa mənbədə varsa yeni sətir
    yaradılmır, mövcud sətrə əlavə mənbə kimi bağlanır (`merged`).
    """
    inserted, skipped, merged = crud.upsert_papers(db, batch.papers)
    source = batch.papers[0].source if batch.papers else None
    crud.add_ingest_run(
        db, fetched=len(batch.papers), inserted=inserted,
        skipped=skipped, merged=merged, source=source,
    )
    if inserted or merged:
        cache.invalidate("analytics:*")
    return IngestResult(
        received=len(batch.papers), inserted=inserted, skipped=skipped, merged=merged
    )


@router.post("/ingest/pull", response_model=PullResult, status_code=201)
def pull(req: PullRequest, db: Session = Depends(get_db)):
    """Server tərəfli yığım: göstərilən mənbədən özü çəkib yazır.

    Hər mənbənin cavab formatı fərqli olduğu üçün parsing Python-da qalır;
    n8n yalnız orkestrasiya edir (cron, retry, error handling).
    """
    module = SOURCES.get(req.source)
    if module is None:
        raise HTTPException(
            status_code=422,
            detail=f"Naməlum mənbə: {req.source}. Mövcud: {', '.join(SOURCES)}",
        )

    targets = req.fields or list(FIELDS)
    unknown = [f for f in targets if f not in FIELDS]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Naməlum sahə: {', '.join(unknown)}")

    since = date.today() - timedelta(days=req.days)
    total_fetched = total_inserted = total_skipped = total_merged = 0
    per_field: dict[str, int] = {}

    for field_key in targets:
        try:
            raw = module.fetch(field_key, since=since, limit=req.limit_per_field, lang=req.lang)
        except Exception as exc:
            crud.add_error(db, workflow=f"ingest/pull:{req.source}", node=field_key, message=str(exc)[:500])
            continue

        papers = [PaperIn(**item) for item in raw]
        inserted, skipped, merged = crud.upsert_papers(db, papers)
        total_fetched += len(papers)
        total_inserted += inserted
        total_skipped += skipped
        total_merged += merged
        per_field[field_key] = inserted

    crud.add_ingest_run(
        db, fetched=total_fetched, inserted=total_inserted,
        skipped=total_skipped, merged=total_merged, source=req.source,
    )
    if total_inserted or total_merged:
        cache.invalidate("analytics:*")

    return PullResult(
        source=req.source, fetched=total_fetched, inserted=total_inserted,
        skipped=total_skipped, merged=total_merged, per_field=per_field,
    )
