from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db
from ..fields import FIELDS
from ..rag.retriever import retrieve
from ..rag.translator import query_to_english
from ..schemas import SearchResponse
from ..security import enforce_search_limits

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search", response_model=SearchResponse)
def semantic_search(
    request: Request,
    q: str = Query(min_length=2, max_length=300),
    top_k: int = Query(5, ge=1, le=20),
    field: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Semantik axtarış: az/ru sorğu əvvəlcə ingiliscəyə çevrilir (korpus ingiliscədir),
    field verilibsə yalnız o sahənin kateqoriyalarında axtarılır."""
    enforce_search_limits(request)
    if field and field not in FIELDS:
        raise HTTPException(status_code=422, detail=f"Naməlum sahə: {field}")
    query_en, lang = query_to_english(q)
    blocks = retrieve(db, query_en, top_k=max(top_k * 2, 10), categories=[field] if field else None)

    hits, seen = [], set()
    for b in blocks:
        paper = b["paper"]
        if paper.id in seen:
            continue
        seen.add(paper.id)
        hits.append({"paper": crud.paper_to_out(paper), "score": b["score"]})
        if len(hits) >= top_k:
            break

    return {
        "query": q,
        "lang": lang,
        "query_en": query_en if lang != "en" else None,
        "hits": hits,
    }
