"""Retrieval qatı: vektor, leksik və hibrid.

Phase 2 (§5). Üç qərar burada verilir və hər üçü ölçmə ilə yoxlanılır:

1. **Nəticələr MƏQALƏ səviyyəsindədir.** Əvvəllər `LIMIT` chunk-lara tətbiq
   olunurdu, ona görə bir məqalənin üç chunk-u top-5-i doldura bilirdi və
   istifadəçi 5 yerinə 2 nəticə görürdü (audit W2). İndi hər məqalədən ən yaxşı
   chunk götürülür (`DISTINCT ON`), limit isə məqalələrə tətbiq olunur.

2. **Leksik axtarış dilə görə sütun seçir.** Rusca sorğu `sv_ru`-ya, qalanı
   `sv_en`-ə gedir — rus stemmer-i ingiliscə mətndə mənasız işləyir.

3. **Birləşdirmə RRF-dir, xal cəmi deyil.** Cosine oxşarlığı [0,1], `ts_rank_cd`
   isə qeyri-məhdud və paylanması tamam fərqlidir; onları toplamaq üçün
   normallaşdırma lazımdır və normallaşdırma sorğudan-sorğuya sürüşür.
   Reciprocal Rank Fusion yalnız SIRALAMADAN istifadə edir, ona görə miqyas
   problemi ümumiyyətlə yaranmır.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .. import models

# RRF sabiti. Standart dəyər 60-dır (Cormack et al. 2009); yüksək k ilk
# yerlərin üstünlüyünü yumşaldır, aşağı k onları kəskinləşdirir.
RRF_K = 60

# Namizəd hovuzu: birləşdirmədən əvvəl hər üsuldan neçə məqalə götürülsün.
# Son limitdən böyük olmalıdır, əks halda birləşdirmənin seçəcəyi bir şey qalmır.
CANDIDATE_MULTIPLIER = 4
MIN_CANDIDATES = 30

_PAPER_LOADS = (
    selectinload(models.Paper.authors),
    selectinload(models.Paper.categories),
    selectinload(models.Paper.sources),
)


def _candidate_count(top_k: int) -> int:
    return max(top_k * CANDIDATE_MULTIPLIER, MIN_CANDIDATES)


# ---------------------------------------------------------------- vektor
def vector_search(
    db: Session,
    question: str,
    top_k: int,
    fields: list[str] | None = None,
    also: str | None = None,
) -> list[dict]:
    """pgvector cosine — məqalə səviyyəsində, hər məqalədən ən yaxın chunk.

    `also` verilibsə (adətən sorğunun ingiliscə tərcüməsi), iki vektorla axtarılır
    və hər chunk üçün daha yaxını götürülür. Səbəb: model çoxdillidir, orijinal
    rusca sorğu rusca sənədləri tapır, tərcümə isə ingiliscə sənədlərdə dəqiqdir —
    yalnız tərcümə ilə axtarsaq rusdilli korpus görünməz qalır.
    """
    # Lokal import: fastembed onnxruntime ilə birlikdə ~250 MB-dır və modul
    # səviyyəsində import olunanda RRF kimi saf funksiyaları test etmək üçün də
    # tələb olunurdu. Bu şəkildə leksik axtarış və birləşdirmə modeldən asılı deyil.
    from .embedder import embed_texts

    texts = [question] + ([also] if also and also.strip() != question.strip() else [])
    vectors = embed_texts(texts)

    distance = models.Chunk.embedding.cosine_distance(vectors[0])
    if len(vectors) > 1:
        distance = func.least(distance, models.Chunk.embedding.cosine_distance(vectors[1]))

    # Hər məqalədən yalnız ən yaxın chunk — DISTINCT ON Postgres-də sıralamanı
    # da özü aparır, ona görə əlavə alt-sorğu lazım deyil.
    inner = (
        select(
            models.Chunk.paper_id.label("paper_id"),
            models.Chunk.id.label("chunk_id"),
            distance.label("distance"),
        )
        .join(models.Paper, models.Chunk.paper_id == models.Paper.id)
        .distinct(models.Chunk.paper_id)
        .order_by(models.Chunk.paper_id, distance)
    )
    if fields:
        inner = inner.where(models.Paper.field_keys.overlap(fields))

    sub = inner.subquery()
    rows = db.execute(
        select(sub.c.paper_id, sub.c.chunk_id, sub.c.distance)
        .order_by(sub.c.distance)
        .limit(top_k)
    ).all()

    return [
        {"paper_id": r.paper_id, "chunk_id": r.chunk_id, "score": round(1.0 - float(r.distance), 4)}
        for r in rows
    ]


# ---------------------------------------------------------------- leksik
def lexical_search(
    db: Session,
    question: str,
    top_k: int,
    lang: str = "en",
    fields: list[str] | None = None,
) -> list[dict]:
    """Postgres tam mətn axtarışı (`ts_rank_cd`), başlıq ağırlıqlı.

    `websearch_to_tsquery` seçilib, çünki istifadəçinin yazdığı sərbəst mətni
    (dırnaq, OR, mənfi termin) qəbul edir və sintaksis xətası atmır —
    `to_tsquery` isə istifadəçi girişində asanlıqla partlayır.
    """
    config, column = ("russian", models.Paper.sv_ru) if lang == "ru" else ("english", models.Paper.sv_en)
    tsquery = func.websearch_to_tsquery(config, question)

    # ts_rank_cd sənədin uzunluğunu nəzərə alır (normalizasiya bayrağı 32),
    # əks halda uzun abstraktlar sırf uzunluğuna görə önə çıxır.
    rank = func.ts_rank_cd(column, tsquery, 32)

    stmt = (
        select(models.Paper.id.label("paper_id"), rank.label("rank"))
        .where(column.op("@@")(tsquery))
        .order_by(rank.desc())
        .limit(top_k)
    )
    if fields:
        stmt = stmt.where(models.Paper.field_keys.overlap(fields))

    rows = db.execute(stmt).all()
    return [{"paper_id": r.paper_id, "chunk_id": None, "score": round(float(r.rank), 4)} for r in rows]


# ---------------------------------------------------------------- birləşdirmə
def rrf_fuse(rankings: list[list[dict]], top_k: int) -> list[dict]:
    """Reciprocal Rank Fusion: score = Σ 1/(k + sıra).

    Xal miqyaslarını normallaşdırmağa ehtiyac qoymur — yalnız sıralar sayılır.
    Hər iki üsulda görünən sənəd təbii olaraq yuxarı qalxır.
    """
    fused: dict[int, dict] = {}
    for ranking in rankings:
        for position, item in enumerate(ranking, start=1):
            pid = item["paper_id"]
            entry = fused.setdefault(
                pid, {"paper_id": pid, "chunk_id": None, "rrf": 0.0, "parts": {}}
            )
            entry["rrf"] += 1.0 / (RRF_K + position)
            # chunk yalnız vektor axtarışından gəlir; kontekst üçün saxlanılır
            if item.get("chunk_id") and not entry["chunk_id"]:
                entry["chunk_id"] = item["chunk_id"]
            entry["parts"][len(entry["parts"])] = item["score"]

    ordered = sorted(fused.values(), key=lambda e: e["rrf"], reverse=True)[:top_k]
    for entry in ordered:
        entry["score"] = round(entry.pop("rrf"), 6)
        entry.pop("parts", None)
    return ordered


# ---------------------------------------------------------------- ictimai API
def retrieve(
    db: Session,
    question: str,
    top_k: int = 5,
    categories: list[str] | None = None,
    also: str | None = None,
    lang: str = "en",
    mode: str = "hybrid",
) -> list[dict]:
    """Sorğuya uyğun məqalələri qaytarır: [{chunk, paper, score}].

    mode: "vector" | "lexical" | "hybrid". Produksiya dəyəri konfiqurasiyadan
    gəlir ki, benchmark eyni funksiyanı çağıra bilsin (ölçdüyümüz davranışla
    istifadəçinin gördüyü davranış ayrılmasın).

    `categories` əslində sahə açarlarıdır — bütün mənbələr üçün işləyən filtr.
    """
    pool = _candidate_count(top_k)

    if mode == "vector":
        hits = vector_search(db, question, top_k, categories, also)
    elif mode == "lexical":
        hits = lexical_search(db, question, top_k, lang, categories)
    else:
        rankings = [
            vector_search(db, question, pool, categories, also),
            lexical_search(db, question, pool, lang, categories),
        ]
        # Rusca sorğuda tərcümə də ayrıca leksik sıralama verir: orijinal rusca
        # termin rusdilli məqalələri, tərcümə isə ingiliscə korpusu tutur.
        if also and also.strip() != question.strip():
            rankings.append(lexical_search(db, also, pool, "en", categories))
        hits = rrf_fuse(rankings, top_k)

    return _hydrate(db, hits)


def _hydrate(db: Session, hits: list[dict]) -> list[dict]:
    """paper_id/chunk_id → real obyektlər, sıralama qorunmaqla.

    Leksik nəticələrdə chunk olmur; onlar üçün məqalənin ilk chunk-u götürülür,
    çünki LLM konteksti mətn tələb edir.
    """
    if not hits:
        return []

    paper_ids = [h["paper_id"] for h in hits]
    papers = {
        p.id: p
        for p in db.scalars(
            select(models.Paper).options(*_PAPER_LOADS).where(models.Paper.id.in_(paper_ids))
        )
    }

    chunk_ids = [h["chunk_id"] for h in hits if h["chunk_id"]]
    chunks = {
        c.id: c
        for c in db.scalars(select(models.Chunk).where(models.Chunk.id.in_(chunk_ids)))
    } if chunk_ids else {}

    # chunk-suz məqalələr üçün ilk chunk
    missing = [h["paper_id"] for h in hits if not h["chunk_id"]]
    first_chunks: dict[int, models.Chunk] = {}
    if missing:
        rows = db.scalars(
            select(models.Chunk)
            .where(models.Chunk.paper_id.in_(missing))
            .distinct(models.Chunk.paper_id)
            .order_by(models.Chunk.paper_id, models.Chunk.chunk_index)
        ).all()
        first_chunks = {c.paper_id: c for c in rows}

    out = []
    for h in hits:
        paper = papers.get(h["paper_id"])
        if paper is None:
            continue
        chunk = chunks.get(h["chunk_id"]) if h["chunk_id"] else first_chunks.get(h["paper_id"])
        if chunk is None:
            continue
        out.append({"chunk": chunk, "paper": paper, "score": h["score"]})
    return out
