"""Research intelligence endpoint-ləri — Phase 4 (§7, §9, §10, §11, §12, §13).

Hamısı eyni qaydaya tabedir: nəticə YALNIZ indekslənmiş korpusdan gəlir və
cavabda korpus konteksti qaytarılır (§16). LLM tələb edən endpoint-lər
(`/compare`, `/conflicts`) `/api/ask` ilə eyni limitlərə tabedir — onlar da
Groq kvotasını xərcləyir.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import auth, cache, crud, models, plans
from ..config import settings
from ..database import get_db
from ..fields import FIELDS
from ..landscape import build_landscape, find_gaps, insight_coverage
from ..relations import RELATION_TYPES, summarize_relations
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
    user: models.User = Depends(auth.require_capability(plans.COMPARE)),
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
        # Keşdən gələn nəticə bizə heç nəyə başa gəlmir — kredit yazılmır.
        return {**cached, "from_cache": True}

    payload = [{"title": p.title, "abstract": p.abstract} for p in papers]
    try:
        result = compare_papers(payload)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Groq xətası: {exc}") from exc

    auth.charge(db, user, plans.COMPARE, {"papers": len(papers)})

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
    user: models.User = Depends(auth.require_capability(plans.CONFLICTS)),
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

    auth.charge(db, user, plans.CONFLICTS, {"papers": len(papers)})

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
    user: models.User = Depends(auth.require_capability(plans.GAPS)),
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
    result = find_gaps(papers, insights, lang)
    auth.charge(db, user, plans.GAPS, {"query": q[:100]})
    return {"query": q, "gaps": result, "corpus": corpus}


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

    # Açar versiyası v2: hesablama dəyişdi (indeks əhatəsi yoxlaması əlavə
    # olundu). Köhnə açarda 6 saatlıq keşdə YANLIŞ təsnifat qalırdı —
    # «təbiət elmləri yeni yaranır». Hesablama məntiqi dəyişəndə açar da
    # dəyişməlidir, yoxsa düzəliş istifadəçiyə çatmır.
    value, hit = cache.get_or_set(
        f"analytics:trendclass:v2:{weeks}", settings.analytics_cache_ttl, build
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


# ---------------------------------------------------------------- §15 relations

@router.get("/papers/{paper_id}/relations")
def paper_relations(
    paper_id: int,
    relation: str | None = Query(None),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Bir məqalənin digərləri ilə əlaqələri (§15).

    Əlaqələr İKİ İSTİQAMƏTDƏ qaytarılır: məqalə həm istinad edən, həm istinad
    olunan ola bilər və istifadəçi üçün hər ikisi maraqlıdır.

    Cavabda `confidence` və `source` mütləq qalır — `cites` xarici reyestrdən
    gələn FAKTdır (1.0), `related_to` isə ölçülmüş oxşarlıqdır (~0.6). Onları
    eyni etibarla göstərmək sistemi inandırıcı görünən uydurmaya çevirərdi.
    """
    if db.get(models.Paper, paper_id) is None:
        raise HTTPException(status_code=404, detail="Məqalə tapılmadı")
    if relation and relation not in RELATION_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Naməlum əlaqə tipi: {relation}. Mövcud: {', '.join(RELATION_TYPES)}",
        )

    stmt = select(models.PaperRelation).where(
        (models.PaperRelation.from_paper_id == paper_id)
        | (models.PaperRelation.to_paper_id == paper_id)
    )
    if relation:
        stmt = stmt.where(models.PaperRelation.relation == relation)
    rows = db.scalars(
        stmt.order_by(models.PaperRelation.confidence.desc()).limit(limit)
    ).all()

    other_ids = {r.to_paper_id if r.from_paper_id == paper_id else r.from_paper_id for r in rows}
    others = {p.id: p for p in _papers_by_ids(db, list(other_ids))}

    out = []
    for r in rows:
        other_id = r.to_paper_id if r.from_paper_id == paper_id else r.from_paper_id
        other = others.get(other_id)
        if other is None:
            continue
        out.append({
            "relation": r.relation,
            # İstiqamət göstərilir: «bu məqalə istinad edir» ilə «buna istinad
            # edilir» tamam fərqli məlumatdır
            "direction": "outgoing" if r.from_paper_id == paper_id else "incoming",
            "confidence": round(r.confidence or 0, 3),
            "source": r.source,
            "evidence": r.evidence,
            "paper": {
                "id": other.id, "title": other.title,
                "doi": other.doi, "arxiv_id": other.arxiv_id,
                "published_at": other.published_at,
            },
        })

    return {
        "paper_id": paper_id,
        "relations": out,
        "summary": summarize_relations([
            {"relation": r.relation, "confidence": r.confidence} for r in rows
        ]),
        "note": (
            "confidence 1.0 = xarici reyestrdən gələn fakt (sitat); "
            "aşağı dəyərlər hesablanmış və ya ölçülmüş əlaqədir."
        ),
    }
