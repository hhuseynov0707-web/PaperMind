from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .. import models
from .embedder import embed_texts


def retrieve(
    db: Session,
    question: str,
    top_k: int = 5,
    categories: list[str] | None = None,
    also: str | None = None,
) -> list[dict]:
    """Sualı embed edib pgvector cosine məsafəsi ilə ən yaxın chunk-ları tapır.

    `also` verilibsə (adətən sorğunun ingiliscə tərcüməsi), axtarış İKİ vektorla
    aparılır və hər chunk üçün daha yaxın olanı götürülür. Səbəb: model çoxdilli
    olduğu üçün orijinal rusca sorğu rusca sənədləri tapır, tərcümə isə ingiliscə
    sənədlərdə daha dəqiqdir — yalnız tərcümə ilə axtarsaq rusdilli korpus
    görünməz qalır.

    categories verilibsə, axtarış yalnız həmin sahələrdə gedir.
    score = 1 - cosine_distance.
    """
    texts = [question] + ([also] if also and also.strip() != question.strip() else [])
    vectors = embed_texts(texts)

    distance = models.Chunk.embedding.cosine_distance(vectors[0])
    if len(vectors) > 1:
        distance = func.least(distance, models.Chunk.embedding.cosine_distance(vectors[1]))
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
