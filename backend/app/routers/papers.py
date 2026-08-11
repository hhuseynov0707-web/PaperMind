from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from .. import cache, crud
from ..config import settings
from ..database import get_db
from ..fields import FIELDS
from ..schemas import FieldOut, PaperOut, PapersPage

router = APIRouter(prefix="/api", tags=["papers"])


@router.get("/papers/featured", response_model=list[PaperOut])
def featured(limit: int = Query(6, ge=1, le=12), db: Session = Depends(get_db)):
    """Yan paneldəki "Kəşf et" kartı üçün təsadüfi seçmələr (hər çağırışda fərqli)."""
    return crud.featured_papers(db, limit)


@router.get("/fields", response_model=list[FieldOut])
def list_fields(response: Response, db: Session = Depends(get_db)):
    """Sahə seçicisi üçün: hər texnologiya sahəsində neçə məqalə var."""
    value, hit = cache.get_or_set(
        "analytics:fields:v3", settings.analytics_cache_ttl, lambda: crud.field_counts(db, FIELDS)
    )
    response.headers["X-Cache"] = "HIT" if hit else "MISS"
    return value


@router.get("/papers", response_model=PapersPage)
def list_papers(
    category: str | None = None,
    field: str | None = Query(None),
    days: int | None = Query(None, ge=1, le=365),
    q: str | None = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if field and field not in FIELDS:
        raise HTTPException(status_code=422, detail=f"Naməlum sahə: {field}")
    items, total = crud.get_papers(
        db, category=category, days=days, q=q,
        page=page, page_size=page_size, field=field,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}
