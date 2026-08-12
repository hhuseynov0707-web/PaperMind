import hashlib
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import cache, crud
from ..config import settings
from ..database import get_db
from ..fields import FIELDS
from ..rag.evidence import citation_label, select_evidence, validate_citations
from ..rag.llm import ask_llm
from ..rag.retriever import retrieve
from ..rag.translator import retrieval_inputs
from ..schemas import AskRequest, AskResponse
from ..security import enforce_ask_limits

router = APIRouter(prefix="/api", tags=["ask"])


def _normalize(q: str) -> str:
    return " ".join(q.lower().split())


EMPTY_DB_MSG = {
    "az": "Bazada hələ məqalə yoxdur — əvvəlcə backfill skriptini və ya n8n ingest workflow-unu işlət.",
    "ru": "В базе пока нет статей — сначала запусти скрипт backfill или n8n ingest workflow.",
    "en": "No papers in the database yet — run the backfill script or the n8n ingest workflow first.",
}


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, request: Request, db: Session = Depends(get_db)):
    """RAG sual-cavab: cache -> (tərcümə) -> retrieval -> Groq -> cavab + mənbələr.

    Retrieval ingiliscə tərcümə ilə gedir, LLM-ə isə orijinal sual verilir —
    cavab istifadəçinin dilində qayıdır (system prompt qaydası).
    """
    if req.field and req.field not in FIELDS:
        raise HTTPException(status_code=422, detail=f"Naməlum sahə: {req.field}")

    # Keşdən gələn cavab da sayılır — əks halda limit asanca keçilər
    enforce_ask_limits(request)

    t0 = time.perf_counter()
    key = (
        f"ask:{hashlib.sha256(_normalize(req.question).encode()).hexdigest()}"
        f":{req.top_k}:{req.field or 'all'}"
    )

    cached = cache.get_json(key)
    if cached:
        latency = int((time.perf_counter() - t0) * 1000)
        crud.save_qa(db, req.question, cached["answer"], cached["sources"], True, latency)
        return AskResponse(
            answer=cached["answer"],
            sources=cached["sources"],
            from_cache=True,
            latency_ms=latency,
            query_en=cached.get("query_en"),
            grounding=cached.get("grounding"),
        )

    query, also, lang, query_en = retrieval_inputs(req.question)
    blocks = retrieve(
        db, query, top_k=req.top_k,
        categories=[req.field] if req.field else None, also=also,
        lang=lang, mode=settings.retrieval_mode,
    )
    if not blocks:
        latency = int((time.perf_counter() - t0) * 1000)
        return AskResponse(
            answer=EMPTY_DB_MSG.get(lang, EMPTY_DB_MSG["en"]),
            sources=[],
            from_cache=False,
            latency_ms=latency,
        )

    if not settings.groq_api_key:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY təyin olunmayıb. .env faylını doldur və 'docker compose restart backend' işlət.",
        )

    # §8: retrieval nə qaytarsa hamısı LLM-ə getmirdi — zəif nəticələr
    # (score 0.2) konteksti çirkləndirirdi. İndi hədd tətbiq olunur.
    blocks, ev_stats = select_evidence(blocks, max_blocks=req.top_k)

    try:
        answer = ask_llm(req.question, blocks, lang=lang)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Groq xətası: {exc}") from exc

    # §8: LLM-in yazdığı hər istinad kontekstlə tutuşdurulur. Kontekstdə
    # olmayan istinad uydurulmuşdur və mətndən çıxarılır — interfeys istinadları
    # vurğulayır, saxta istinad orada həqiqi kimi görünür.
    allowed = {citation_label(b["paper"]) for b in blocks}
    answer, cite_stats = validate_citations(answer, allowed)

    sources, seen = [], set()
    for b in blocks:
        paper = b["paper"]
        if paper.id in seen:
            continue
        seen.add(paper.id)
        sources.append(
            {
                "arxiv_id": paper.arxiv_id,
                "doi": paper.doi,
                "title": paper.title,
                "score": b["score"],
                "pdf_url": paper.pdf_url,
            }
        )

    grounding = {
        "evidence_used": ev_stats["kept"],
        "evidence_dropped": ev_stats["dropped"],
        "top_score": ev_stats["top_score"],
        "weak": ev_stats["weak"],
        "citations_valid": cite_stats["valid"],
        "citations_removed": cite_stats["invented"],
        "coverage": cite_stats["coverage"],
    }

    query_en_out = query_en if lang != "en" else None
    latency = int((time.perf_counter() - t0) * 1000)
    cache.set_json(
        key,
        {"answer": answer, "sources": sources, "query_en": query_en_out,
         "grounding": grounding},
        settings.ask_cache_ttl,
    )
    crud.save_qa(db, req.question, answer, sources, False, latency)
    return AskResponse(
        answer=answer,
        sources=sources,
        from_cache=False,
        latency_ms=latency,
        query_en=query_en_out,
        grounding=grounding,
    )
