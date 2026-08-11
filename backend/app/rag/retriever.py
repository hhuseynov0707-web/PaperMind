from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import models
from .embedder import embed_query


def retrieve(
    db: Session,
    question: str,
    top_k: int = 5,
    categories: list[str] | None = None,
) -> list[dict]:
    """Sualı embed edib pgvector cosine məsafəsi ilə ən yaxın chunk-ları tapır.

    categories verilibsə, axtarış yalnız həmin arXiv kateqoriyalarında
    (cross-listing daxil) gedir. score = 1 - cosine_distance.
    """
    qvec = embed_query(question)
    distance = models.Chunk.embedding.cosine_distance(qvec)
    stmt = (
        select(models.Chunk, models.Paper, distance.label("distance"))
        .join(models.Paper, models.Chunk.paper_id == models.Paper.id)
        .options(
            selectinload(models.Paper.authors),
            selectinload(models.Paper.categories),
            selectinload(models.Paper.sources),
        )
    )
    if categories:
        # `categories` əslində sahə açarlarıdır — bütün mənbələr üçün işləyən filtr
        stmt = stmt.where(models.Paper.field_keys.overlap(categories))
    rows = db.execute(stmt.order_by(distance).limit(top_k)).all()
    return [
        {"chunk": row.Chunk, "paper": row.Paper, "score": round(1.0 - float(row.distance), 4)}
        for row in rows
    ]
