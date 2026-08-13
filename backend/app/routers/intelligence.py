"""Research intelligence endpoint-ləri — Phase 4 (§7, §9, §10, §11, §12, §13).

Hamısı eyni qaydaya tabedir: nəticə YALNIZ indekslənmiş korpusdan gəlir və
cavabda korpus konteksti qaytarılır (§16). LLM tələb edən endpoint-lər
(`/compare`, `/conflicts`) `/api/ask` ilə eyni limitlərə tabedir — onlar da
Groq kvotasını xərcləyir.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import cache, crud, models
from ..config import settings
from ..database import get_db
from ..fields import FIELDS
from ..landscape import build_landscape, find_gaps, insight_coverage
from ..rag.compare import assess_conflict, compare_papers
from ..rag.insights import evidence_summary
from ..rag.retriever import retrieve
from ..rag.translator import retrieval_inputs
from ..security import enforce_ask_limits, enforce_search_limits
from ..trends import classify_series

router = APIRouter(prefix="/api", tags=["intelligence"])

MAX_COMPARE = 5
LANDSCAPE_POOL = 60


def _load_insights(db: Session, paper_ids: list[int]) -> dict[int, dict]:
    if not paper_ids:
        return {}
    rows = db.scalars(
        select(models.PaperInsight).where(models.PaperInsight.paper_id.in_(paper_ids))
    ).all()
    return {r.paper_id: (r.data or {}) for r in rows}


def _papers_by_ids(db: Session, ids: list[int]) -> list[models.Paper]:
    """Verilən sıra ilə məqalələri yükləyir (sıra istinad nömrələri üçün vacibdir)."""
    rows = db.scalars(
        select(models.Paper)
        .options(selectinload(models.Paper.authors), selectinload(models.Paper.sources))
        .where(models.Paper.id.in_(ids))
    ).all()
    by_id = {p.id: p for p in rows}
    return [by_id[i] for i in ids if i in by_id]


# ---------------------------------------------------------------- §7 insights

@router.get("/papers/{paper_id}/insights")
def paper_insights(paper_id: int, db: Session = Depends(get_db)):
    """Bir məqalənin strukturlu çıxarışı.

    Çıxarış yoxdursa 404 qaytarılır — boş obyekt qaytarmaq «bu məqalədə
    məhdudiyyət yoxdur» kimi oxuna bilər, halbuki sadəcə hesablanmayıb.
    """
    paper = db.get(models.Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Məqalə tapılmadı")

    row = db.get(models.PaperInsight, paper_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Bu məqalə üçün çıxarış hələ hesablanmayıb (scripts/extract_insights.py).",
        )

    return {
        "paper_id": paper_id,
        "title": paper.title,
        "insights": row.data or {},
        "evidence": evidence_summary(row.data or {}),
        "model": row.model,
        # §7: çıxarışın nəyə əsaslandığı gizlədilmir
        "basis": "abstract_only",
    }


# ---------------------------------------------------------------- §9 compare

@router.post("/compare")
def compare(
    request: Request,
    paper_ids: list[int],
    db: Session = Depends(get_db),
):
    """İki-beş məqaləni oxlar üzrə müqayisə edir (§9).

    Ayrı-ayrı xülasə DEYİL: razılıq, fərq və müqayisə oluna bilməyən oxlar
    göstərilir.
    """
    if not 2 <= len(paper_ids) <= MAX_COMPARE:
        raise HTTPException(status_code=422, detail=f"2–{MAX_COMPARE} məqalə tələb olunur")
    if not settings.groq_api_key:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY təyin olunmayıb")

    enforce_ask_limits(request)   # LLM xərci — /api/ask ilə eyni büdcə

    papers = _papers_by_ids(db, paper_ids)
    if len(papers) < 2:
        raise HTTPException(status_code=404, detail="Məqalələrin hamısı tapılmadı")

    key = "cmp:" + ",".join(str(p.id) for p in papers)
    cached = cache.get_json(key)
    if cached:
        return {**cached, "from_cache": True}

    payload = [{"title": p.title, "abstract": p.abstract} for p in papers]
    try:
        result = compare_papers(payload)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Groq xətası: {exc}") from exc

    out = {
        "comparison": result,
        "papers": [
            {"n": i, "id": p.id, "title": p.title, "doi": p.doi, "arxiv_id": p.arxiv_id}
            for i, p in enumerate(papers, start=1)
        ],
        "basis": "abstract_only",
        "from_cache": False,
    }
    cache.set_json(key, out, settings.ask_cache_ttl)
    return out


# ---------------------------------------------------------------- §10 conflicts

@router.post("/conflicts")
def conflicts(
    request: Request,
    paper_ids: list[int],
    question: str | None = Query(None, max_length=300),
    db: Session = Depends(get_db),
):
    """Məqalələr arasında ziddiyyətin təsnifatı (§10).

    Sistem HANSI məqalənin doğru olduğunu demir — yalnız ziddiyyətin tipini və
    onu doğuran şərtləri göstərir.
    """
    if not 2 <= len(paper_ids) <= MAX_COMPARE:
        raise HTTPException(status_code=422, detail=f"2–{MAX_COMPARE} məqalə tələb olunur")
    if not settings.groq_api_key:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY təyin olunmayıb")

    enforce_ask_limits(request)

    papers = _papers_by_ids(db, paper_ids)
    if len(papers) < 2:
        raise HTTPException(status_code=404, detail="Məqalələrin hamısı tapılmadı")

    payload = [{"title": p.title, "abstract": p.abstract} for p in papers]
    try:
        result = assess_conflict(payload, question)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Groq xətası: {exc}") from exc

    return {
        "assessment": result,
        "papers": [
            {"n": i, "id": p.id, "title": p.title, "doi": p.doi, "arxiv_id": p.arxiv_id}
            for i, p in enumerate(papers, start=1)
        ],
        "basis": "abstract_only",
        # §10: qərar istifadəçinindir
        "note": "Sistem hansı məqalənin doğru olduğunu təyin etmir; sübutu göstərir.",
    }


# ---------------------------------------------------------------- §11 landscape

@router.get("/landscape")
def landscape(
    request: Request,
    q: str = Query(min_length=2, max_length=300),
    limit: int = Query(LANDSCAPE_POOL, ge=10, le=120),
    db: Session = Depends(get_db),
):
    """Mövzu üzrə tədqiqat landşaftı (§11) — real indekslənmiş ədəbiyyatdan."""
    enforce_search_limits(request)

    query, also, lang, query_en = retrieval_inputs(q)
    blocks = retrieve(db, query, top_k=limit, also=also, lang=lang,
                      mode=settings.retrieval_mode)
    papers = [b["paper"] for b in blocks]
    insights = _load_insights(db, [p.id for p in papers])

    corpus, _ = cache.get_or_set(
        "analytics:corpus:v1", settings.analytics_cache_ttl,
        lambda: crud.corpus_snapshot(db),
    )
    return {
        "query": q,
        "query_en": query_en if lang != "en" else None,
        "landscape": build_landscape(papers, insights),
        "insight_coverage": insight_coverage(insights),
        "corpus": corpus,
    }


# ---------------------------------------------------------------- §13 gaps

@router.get("/gaps")
def gaps(
    request: Request,
    q: str = Query(min_length=2, max_length=300),
    limit: int = Query(LANDSCAPE_POOL, ge=10, le=120),
    lang: str = Query("az", pattern="^(az|ru|en)$"),
    db: Session = Depends(get_db),
):
    """Potensial tədqiqat boşluqları (§13) — AI nəticəsi kimi etiketlənir."""
    enforce_search_limits(request)

    query, also, detected, _ = retrieval_inputs(q)
    blocks = retrieve(db, query, top_k=limit, also=also, lang=detected,
                      mode=settings.retrieval_mode)
    papers = [b["paper"] for b in blocks]
    insights = _load_insights(db, [p.id for p in papers])

    corpus, _ = cache.get_or_set(
        "analytics:corpus:v1", settings.analytics_cache_ttl,
        lambda: crud.corpus_snapshot(db),
    )
    return {"query": q, "gaps": find_gaps(papers, insights, lang), "corpus": corpus}


# ---------------------------------------------------------------- §12 trends

@router.get("/analytics/trend-classes")
def trend_classes(
    response: Response,
    weeks: int = Query(16, ge=8, le=52),
    db: Session = Depends(get_db),
):
    """Fənn qruplarının trend təsnifatı (§12) — səbəbi ilə birlikdə."""
    def build():
        rows = crud.trends(db, weeks=weeks)
        # {qrup: {həftə: say}} — sonra sıralı seriyaya çevrilir
        buckets: dict[str, dict[str, int]] = {}
        all_weeks: set[str] = set()
        for r in rows:
            week = str(r["week"])[:10]
            all_weeks.add(week)
            buckets.setdefault(r["category"], {})[week] = r["count"]

        ordered_weeks = sorted(all_weeks)
        # Boş həftələr SIFIRLA doldurulur — onsuz "azalma" görünməz qalır
        series = {
            name: [counts.get(w, 0) for w in ordered_weeks]
            for name, counts in buckets.items()
        }
        return {"weeks": ordered_weeks, "classes": classify_series(series)}

    value, hit = cache.get_or_set(
        f"analytics:trendclass:v1:{weeks}", settings.analytics_cache_ttl, build
    )
    response.headers["X-Cache"] = "HIT" if hit else "MISS"
    return value


# ---------------------------------------------------------------- §14 cross-disciplinary

@router.get("/cross-disciplinary")
def cross_disciplinary(
    request: Request,
    q: str = Query(min_length=2, max_length=300),
    limit: int = Query(LANDSCAPE_POOL, ge=10, le=120),
    db: Session = Depends(get_db),
):
    """Fənlərarası əlaqələr (§14) — yalnız ədəbiyyatla dəstəklənənlər.

    Metod: sorğuya uyğun məqalələr tapılır və HANSI SAHƏLƏRİN birlikdə göründüyü
    sayılır. Əlaqə uydurulmur — bir məqalə eyni anda iki sahəyə aiddirsə, bu,
    həmin məqalənin özünün faktıdır.
    """
    enforce_search_limits(request)

    query, also, lang, query_en = retrieval_inputs(q)
    blocks = retrieve(db, query, top_k=limit, also=also, lang=lang,
                      mode=settings.retrieval_mode)
    papers = [b["paper"] for b in blocks]

    from collections import Counter
    pairs = Counter()
    bridges: dict[tuple, list] = {}
    for p in papers:
        keys = sorted(set(p.field_keys or []))
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                pairs[(a, b)] += 1
                bridges.setdefault((a, b), []).append(
                    {"id": p.id, "title": p.title, "doi": p.doi, "arxiv_id": p.arxiv_id}
                )

    known = set(FIELDS)
    connections = [
        {
            "fields": [a, b],
            "papers": count,
            # Sübut: əlaqəni yaradan konkret məqalələr
            "evidence": bridges[(a, b)][:3],
        }
        for (a, b), count in pairs.most_common(15)
        if a in known and b in known
    ]

    return {
        "query": q,
        "query_en": query_en if lang != "en" else None,
        "connections": connections,
        "examined": len(papers),
        "note": (
            "Əlaqələr yalnız indekslənmiş məqalələrin öz sahə təsnifatından çıxarılır; "
            "sistem əlaqə uydurmur."
        ),
    }
