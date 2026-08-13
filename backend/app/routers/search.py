from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from .. import crud
from ..config import settings
from ..database import get_db
from ..fields import FIELDS
from ..rag.retriever import retrieve
from ..rag.translator import retrieval_inputs
from ..rag.understanding import INTENT_ROUTE, understand
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
    # Dilə görə strategiya translator-də, benchmark ilə ölçülüb
    # §6: sorğudan niyyət və məhdudiyyətlər çıxarılır. `core` — məhdudiyyət
    # ifadələri təmizlənmiş mətndir; `author:LeCun` embedding üçün səs-küydür,
    # filtr kimi isə dəyərlidir.
    plan = understand(q)
    query, also, lang, query_en = retrieval_inputs(plan.core)
    # retrieve() artıq məqalə səviyyəsində qaytarır (audit W2) — əvvəllər
    # chunk-lara limit qoyulduğu üçün top_k*2 çəkib Python-da təkrarları
    # atmaq lazım gəlirdi. İndi buna ehtiyac yoxdur.
    blocks = retrieve(
        db, query, top_k=top_k,
        categories=[field] if field else None, also=also,
        lang=lang, mode=settings.retrieval_mode,
        filters={
            "year_from": plan.year_from,
            "year_to": plan.year_to,
            "authors": plan.authors,
        },
    )
    hits = [{"paper": crud.paper_to_out(b["paper"]), "score": b["score"]} for b in blocks]

    return {
        "plan": {
            **plan.as_dict(),
            # Niyyət SEARCH-dürsə təklif göstərilmir — istifadəçi onsuz da
            # axtarışdadır və lazımsız təklif interfeysi yükləyir.
            "suggested_endpoint": (
                INTENT_ROUTE.get(plan.intent) if plan.intent != "SEARCH" else None
            ),
        },
        "query": q,
        "lang": lang,
        "query_en": query_en if lang != "en" else None,
        "hits": hits,
    }
