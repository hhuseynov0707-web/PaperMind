from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from .. import cache, crud
from ..config import settings
from ..database import get_db
from ..schemas import AuthorStat, SummaryOut, TrendPoint

router = APIRouter(prefix="/api", tags=["analytics"])

# Bu endpoint-lərin hamısı "ağır" GROUP BY sorğularıdır — nəticə Redis-də saxlanılır.
# X-Cache header-i (HIT/MISS) frontend-də fərqi göstərmək üçündür.


@router.get("/analytics/trends", response_model=list[TrendPoint])
def get_trends(
    response: Response,
    weeks: int = Query(8, ge=1, le=52),
    db: Session = Depends(get_db),
):
    value, hit = cache.get_or_set(
        f"analytics:trends:{weeks}", settings.analytics_cache_ttl, lambda: crud.trends(db, weeks)
    )
    response.headers["X-Cache"] = "HIT" if hit else "MISS"
    return value


@router.get("/analytics/top-authors", response_model=list[AuthorStat])
def get_top_authors(
    response: Response,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    value, hit = cache.get_or_set(
        f"analytics:top-authors:{limit}",
        settings.analytics_cache_ttl,
        lambda: crud.top_authors(db, limit),
    )
    response.headers["X-Cache"] = "HIT" if hit else "MISS"
    return value


@router.get("/analytics/summary", response_model=SummaryOut)
def get_summary(response: Response, db: Session = Depends(get_db)):
    value, hit = cache.get_or_set(
        "analytics:summary", settings.analytics_cache_ttl, lambda: crud.summary(db)
    )
    response.headers["X-Cache"] = "HIT" if hit else "MISS"
    return value
