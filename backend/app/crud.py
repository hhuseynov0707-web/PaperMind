from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session, selectinload

from . import models
from .schemas import PaperIn


def paper_to_out(p: models.Paper) -> dict:
    return {
        "id": p.id,
        "arxiv_id": p.arxiv_id,
        "doi": p.doi,
        "title": p.title,
        "abstract": p.abstract,
        "primary_category": p.primary_category,
        "published_at": p.published_at,
        "pdf_url": p.pdf_url,
        "language": p.language or "en",
        "authors": [a.name for a in p.authors],
        "categories": [c.code for c in p.categories],
        "field_keys": list(p.field_keys or []),
        "sources": sorted({s.source for s in p.sources} | {p.source}),
    }


_PAPER_LOADS = (
    selectinload(models.Paper.authors),
    selectinload(models.Paper.categories),
    selectinload(models.Paper.sources),
)


# ---------- Ingest ----------

def _find_existing(db: Session, doi: str | None, arxiv_id: str | None, tkey: str | None):
    """Dublikat axtarışı — güclüdən zəifə doğru üç açar."""
    conditions = []
    if doi:
        conditions.append(models.Paper.doi == doi)
    if arxiv_id:
        conditions.append(models.Paper.arxiv_id == arxiv_id)
    if tkey:
        conditions.append(models.Paper.title_key == tkey)
    if not conditions:
        return None
    return db.scalars(
        select(models.Paper).options(*_PAPER_LOADS).where(or_(*conditions)).limit(1)
    ).first()


def _merge_source(db: Session, paper: models.Paper, p: PaperIn, doi: str | None) -> bool:
    """Mövcud məqaləyə yeni mənbəni bağlayır və çatışmayan sahələri doldurur.

    True qaytarır = bu, yeni mənbə idi (birləşdirildi); False = artıq tanınırdı.
    """
    known = {(s.source, s.external_id) for s in paper.sources}
    is_new_source = (p.source, p.external_id) not in known and p.source != paper.source

    if (p.source, p.external_id) not in known:
        # Əlaqə üzərindən əlavə edilir: partiya daxilində yeni sətrin id-si
        # hələ yoxdur, FK-nı SQLAlchemy flush zamanı özü bağlayır.
        paper.sources.append(
            models.PaperSource(source=p.source, external_id=p.external_id, url=p.pdf_url)
        )

    # Zənginləşdirmə: bir mənbədə olmayan məlumat digərində ola bilər
    if not paper.doi and doi:
        paper.doi = doi
    if not paper.arxiv_id and p.arxiv_id:
        paper.arxiv_id = p.arxiv_id
    if not paper.pdf_url and p.pdf_url:
        paper.pdf_url = p.pdf_url
    if p.field_keys:
        paper.field_keys = sorted(set(paper.field_keys or []) | set(p.field_keys))
    return is_new_source


def upsert_papers(db: Session, papers: list[PaperIn]) -> tuple[int, int, int]:
    """Məqalələri deduplikasiya edərək yazır. (inserted, skipped, merged) qaytarır.

    Eyni iş bir neçə mənbədə varsa YALNIZ BİR sətir saxlanılır; digər mənbələr
    `paper_sources`-a əlavə olunur (`merged`). Beləliklə interfeysdə təkrar
    nəticə görünmür, amma provenans itmir.
    """
    from .rag.chunker import chunk_text
    from .rag.embedder import embed_texts
    from .sources.common import detect_language, normalize_arxiv_id, normalize_doi, title_key

    if not papers:
        return 0, 0, 0

    all_author_names = list({name for p in papers for name in p.authors})
    author_cache: dict[str, models.Author] = {
        a.name: a
        for a in db.scalars(
            select(models.Author).where(models.Author.name.in_(all_author_names))
        )
    }
    cat_cache: dict[str, models.Category] = {
        c.code: c for c in db.scalars(select(models.Category))
    }

    new_papers: list[models.Paper] = []
    chunk_map: list[tuple[models.Paper, list[str]]] = []
    merged = 0
    # Partiya daxilində də dedup — eyni iş iki mənbədən eyni anda gələ bilər
    batch_keys: dict[str, models.Paper] = {}

    for p in papers:
        doi = normalize_doi(p.doi)
        arxiv_id = normalize_arxiv_id(p.arxiv_id)
        tkey = title_key(p.title)

        hit = next((batch_keys[k] for k in (doi, arxiv_id, tkey) if k and k in batch_keys), None)
        if hit is None:
            hit = _find_existing(db, doi, arxiv_id, tkey)

        if hit is not None:
            if _merge_source(db, hit, p, doi):
                merged += 1
            for k in (doi, arxiv_id, tkey):
                if k:
                    batch_keys[k] = hit
            continue

        row = models.Paper(
            source=p.source,
            external_id=p.external_id,
            arxiv_id=arxiv_id,
            doi=doi,
            title_key=tkey,
            language=p.language or detect_language(p.title, p.abstract),
            title=p.title,
            abstract=p.abstract,
            primary_category=p.primary_category,
            field_keys=sorted(set(p.field_keys)),
            published_at=p.published_at,
            pdf_url=p.pdf_url,
        )
        row.sources.append(
            models.PaperSource(source=p.source, external_id=p.external_id, url=p.pdf_url)
        )
        for k in (doi, arxiv_id, tkey):
            if k:
                batch_keys[k] = row
        for name in dict.fromkeys(p.authors):
            author = author_cache.get(name)
            if author is None:
                author = models.Author(name=name)
                db.add(author)
                author_cache[name] = author
            row.authors.append(author)
        for code in dict.fromkeys(p.categories):
            cat = cat_cache.get(code)
            if cat is None:
                cat = models.Category(code=code, name=code)
                db.add(cat)
                cat_cache[code] = cat
            row.categories.append(cat)

        db.add(row)
        new_papers.append(row)
        chunk_map.append((row, chunk_text(p.abstract)))

    # Bütün chunk-ları bir dəfəyə embed etmək tək-tək etməkdən qat-qat sürətlidir
    all_texts = [t for _, texts in chunk_map for t in texts]
    vectors = embed_texts(all_texts)
    i = 0
    from .config import settings

    for paper, texts in chunk_map:
        for idx, content in enumerate(texts):
            paper.chunks.append(
                models.Chunk(
                    chunk_index=idx, content=content, embedding=vectors[i],
                    embedding_model=settings.embedding_model,
                )
            )
            i += 1

    db.commit()
    inserted = len(new_papers)
    return inserted, len(papers) - inserted - merged, merged


# ---------- Papers ----------

def get_papers(
    db: Session,
    category: str | None = None,
    days: int | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    stmt = select(models.Paper).options(*_PAPER_LOADS)
    count_stmt = select(func.count(models.Paper.id))

    if category:
        stmt = stmt.where(models.Paper.primary_category == category)
        count_stmt = count_stmt.where(models.Paper.primary_category == category)
    if days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = stmt.where(models.Paper.published_at >= cutoff)
        count_stmt = count_stmt.where(models.Paper.published_at >= cutoff)
    if q:
        stmt = stmt.where(models.Paper.title.ilike(f"%{q}%"))
        count_stmt = count_stmt.where(models.Paper.title.ilike(f"%{q}%"))

    total = db.scalar(count_stmt) or 0
    rows = db.scalars(
        stmt.order_by(desc(models.Paper.published_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return [paper_to_out(r) for r in rows], total


def featured_papers(db: Session, limit: int = 6) -> list[dict]:
    """Yan panel üçün təsadüfi seçmə məqalələr (son 14 gün, yoxdursa hamıdan)."""
    base = select(models.Paper).options(*_PAPER_LOADS)
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    rows = db.scalars(
        base.where(models.Paper.published_at >= cutoff).order_by(func.random()).limit(limit)
    ).all()
    if not rows:
        rows = db.scalars(base.order_by(func.random()).limit(limit)).all()
    return [paper_to_out(r) for r in rows]


def field_counts(db: Session, fields: dict[str, list[str]]) -> list[dict]:
    """Hər sahə üzrə məqalə sayı — indi bütün mənbələr üçün `field_keys` üzərindən.

    categories də qaytarılır ki, frontend arXiv kateqoriya -> sahə xəritəsini
    təkrar yazmadan, tək mənbədən qursun (trend qrafiki bunu işlədir).
    """
    key_col = func.unnest(models.Paper.field_keys).label("fk")
    rows = db.execute(
        select(key_col, func.count().label("count")).group_by("fk")
    ).all()
    from .fields import FIELD_GROUP

    counts = {r.fk: r.count for r in rows}
    return [
        {
            "key": key,
            "count": counts.get(key, 0),
            "group": FIELD_GROUP.get(key, ""),
            "categories": list(cats),
        }
        for key, cats in fields.items()
    ]


def source_counts(db: Session) -> list[dict]:
    """Mənbə üzrə paylanma — məqalənin görüldüyü hər mənbə sayılır."""
    rows = db.execute(
        select(models.PaperSource.source, func.count(func.distinct(models.PaperSource.paper_id)).label("c"))
        .group_by(models.PaperSource.source)
        .order_by(desc("c"))
    ).all()
    return [{"source": r.source, "count": r.c} for r in rows]


def multi_source_count(db: Session) -> int:
    """Birdən çox mənbədə tapılıb birləşdirilmiş məqalələrin sayı."""
    sub = (
        select(models.PaperSource.paper_id)
        .group_by(models.PaperSource.paper_id)
        .having(func.count(func.distinct(models.PaperSource.source)) > 1)
        .subquery()
    )
    return db.scalar(select(func.count()).select_from(sub)) or 0


# ---------- Analytics (ağır SQL sorğuları — Redis-də keşlənir) ----------

def trends(db: Session, weeks: int = 8) -> list[dict]:
    """Həftələr üzrə SAHƏ paylanması.

    `primary_category` üzrə qruplaşdırmaq olmaz — o, yalnız arXiv-də doludur,
    Crossref/DOAJ/OpenAlex məqalələrinin hamısı "digər" səbətinə düşürdü.
    `field_keys` isə bütün mənbələr üçün təyin olunur.

    Bir məqalə bir neçə sahəyə aid ola bilər və hər sahədə sayılır — trend
    baxışı üçün bu düzgündür (sahənin aktivliyi ölçülür, məqalələr deyil).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    week = func.date_trunc("week", models.Paper.published_at)
    field = func.unnest(models.Paper.field_keys)
    rows = db.execute(
        select(week.label("week"), field.label("category"), func.count().label("count"))
        .where(models.Paper.published_at >= cutoff)
        .group_by(week, field)
        .order_by(week)
    ).all()
    return [
        {"week": r.week.date().isoformat(), "category": r.category, "count": r.count}
        for r in rows
    ]


def top_authors(db: Session, limit: int = 10) -> list[dict]:
    rows = db.execute(
        select(models.Author.name, func.count(models.paper_authors.c.paper_id).label("count"))
        .join(models.paper_authors, models.paper_authors.c.author_id == models.Author.id)
        .group_by(models.Author.name)
        .order_by(desc("count"))
        .limit(limit)
    ).all()
    return [{"name": r.name, "count": r.count} for r in rows]


def summary(db: Session) -> dict:
    total_papers = db.scalar(select(func.count(models.Paper.id))) or 0
    total_chunks = db.scalar(select(func.count(models.Chunk.id))) or 0
    last_run = db.scalars(
        select(models.IngestRun).order_by(desc(models.IngestRun.run_at)).limit(1)
    ).first()
    by_cat = db.execute(
        select(
            func.coalesce(models.Paper.primary_category, "digər").label("category"),
            func.count().label("count"),
        )
        .group_by("category")
        .order_by(desc("count"))
        .limit(8)
    ).all()
    return {
        "total_papers": total_papers,
        "total_chunks": total_chunks,
        "last_ingest": last_run.run_at.isoformat() if last_run else None,
        "by_category": [{"category": r.category, "count": r.count} for r in by_cat],
        "by_source": source_counts(db),
        "multi_source": multi_source_count(db),
    }


# ---------- QA history / Logs / Digest ----------

def save_qa(db: Session, question: str, answer: str, sources: list, from_cache: bool, latency_ms: int) -> None:
    db.add(
        models.QaHistory(
            question=question,
            answer=answer,
            sources=sources,
            from_cache=from_cache,
            latency_ms=latency_ms,
        )
    )
    db.commit()


def recent_questions(db: Session, limit: int = 10):
    return db.scalars(
        select(models.QaHistory).order_by(desc(models.QaHistory.created_at)).limit(limit)
    ).all()


def add_ingest_run(
    db: Session, fetched: int, inserted: int, skipped: int,
    merged: int = 0, source: str | None = None, status: str = "success",
) -> None:
    db.add(models.IngestRun(
        fetched=fetched, inserted=inserted, skipped=skipped,
        merged=merged, source=source, status=status,
    ))
    db.commit()


def recent_ingest_runs(db: Session, limit: int = 10):
    return db.scalars(
        select(models.IngestRun).order_by(desc(models.IngestRun.run_at)).limit(limit)
    ).all()


def add_error(db: Session, workflow: str, node: str | None, message: str) -> models.ErrorLog:
    row = models.ErrorLog(workflow=workflow, node=node, message=message)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def recent_errors(db: Session, limit: int = 20):
    return db.scalars(
        select(models.ErrorLog).order_by(desc(models.ErrorLog.happened_at)).limit(limit)
    ).all()


def upsert_digest(db: Session, week_start, content: str) -> models.Digest:
    row = db.scalars(
        select(models.Digest).where(models.Digest.week_start == week_start)
    ).first()
    if row:
        row.content = content
    else:
        row = models.Digest(week_start=week_start, content=content)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def latest_digest(db: Session):
    return db.scalars(
        select(models.Digest).order_by(desc(models.Digest.created_at)).limit(1)
    ).first()
