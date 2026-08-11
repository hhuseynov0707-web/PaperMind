"""Yüngül, idempotent sxem miqrasiyası (Alembic-siz).

Layihə `Base.metadata.create_all()` işlədir — o, YENİ cədvəl yaradır, amma
mövcud cədvələ sütun ƏLAVƏ ETMİR. Çoxmənbəli dedup üçün lazım olan sütunlar
burada əlavə olunur və köhnə arXiv sətirləri yeni sahələrlə doldurulur.
Hər addım təkrar işləməyə davamlıdır.
"""

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import engine
from .fields import FIELDS

log = logging.getLogger("papermind.migrate")

DDL = [
    "ALTER TABLE papers ADD COLUMN IF NOT EXISTS source text",
    "ALTER TABLE papers ADD COLUMN IF NOT EXISTS external_id text",
    "ALTER TABLE papers ADD COLUMN IF NOT EXISTS doi text",
    "ALTER TABLE papers ADD COLUMN IF NOT EXISTS title_key text",
    "ALTER TABLE papers ADD COLUMN IF NOT EXISTS field_keys text[]",
    "ALTER TABLE papers ADD COLUMN IF NOT EXISTS language text",
    "CREATE INDEX IF NOT EXISTS ix_papers_language ON papers (language)",
    "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS embedding_model text",
    "CREATE INDEX IF NOT EXISTS ix_chunks_embedding_model ON chunks (embedding_model)",
    "ALTER TABLE papers ALTER COLUMN arxiv_id DROP NOT NULL",
    "ALTER TABLE ingest_runs ADD COLUMN IF NOT EXISTS merged integer DEFAULT 0",
    "ALTER TABLE ingest_runs ADD COLUMN IF NOT EXISTS source text",
    "CREATE INDEX IF NOT EXISTS ix_papers_doi ON papers (doi)",
    "CREATE INDEX IF NOT EXISTS ix_papers_title_key ON papers (title_key)",
    "CREATE INDEX IF NOT EXISTS ix_papers_source ON papers (source)",
    "CREATE INDEX IF NOT EXISTS ix_papers_field_keys ON papers USING gin (field_keys)",
]

# Vektor axtarışı üçün ANN indeksi. Bunsuz hər sorğu bütün chunks cədvəlini
# ardıcıl skan edir — bir neçə min sətirdə hiss olunmur, yüz minlərlə sətirdə
# sistem dayanır. Boş cədvəldə yaradılması anidir, ona görə korpus böyüməzdən
# ƏVVƏL qurulur; Postgres sonra onu avtomatik saxlayır.
#
# vector_cosine_ops seçilib, çünki retriever cosine_distance işlədir —
# operator sinfi məsafə funksiyası ilə üst-üstə düşməlidir, yoxsa indeks
# istifadə olunmur.
HNSW_INDEX = (
    "CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw "
    "ON chunks USING hnsw (embedding vector_cosine_ops)"
)


def _backfill_field_keys(conn) -> int:
    """arXiv kateqoriyalarından sahə açarlarını çıxarır."""
    pairs = [(key, code) for key, codes in FIELDS.items() for code in codes]
    values = ", ".join(f"('{k}', '{c}')" for k, c in pairs)
    result = conn.execute(text(f"""
        UPDATE papers p
           SET field_keys = sub.keys
        FROM (
            SELECT pc.paper_id, array_agg(DISTINCT m.key) AS keys
            FROM paper_categories pc
            JOIN (VALUES {values}) AS m(key, code) ON m.code = pc.category_code
            GROUP BY pc.paper_id
        ) sub
        WHERE p.id = sub.paper_id AND (p.field_keys IS NULL OR p.field_keys = '{{}}')
    """))
    return result.rowcount or 0


def run() -> None:
    with engine.begin() as conn:
        for stmt in DDL:
            conn.execute(text(stmt))

    # Ayrıca tranzaksiyada: böyük cədvəldə uzun çəkə bilər və uğursuzluğu
    # qalan miqrasiyanı dayandırmamalıdır (sistem indekssiz də işləyir, sadəcə yavaş).
    try:
        with engine.begin() as conn:
            conn.execute(text(HNSW_INDEX))
        log.info("HNSW vektor indeksi hazırdır")
    except Exception as exc:
        log.warning("HNSW indeksi yaradıla bilmədi (sistem indekssiz işləyəcək): %s", exc)

        # Köhnə sətirlər arXiv mənşəlidir
        conn.execute(text("""
            UPDATE papers
               SET source = 'arxiv', external_id = COALESCE(external_id, arxiv_id)
             WHERE source IS NULL
        """))
        conn.execute(text("ALTER TABLE papers ALTER COLUMN source SET DEFAULT 'arxiv'"))

        moved = _backfill_field_keys(conn)
        if moved:
            log.info("field_keys dolduruldu: %s sətir", moved)

        # Provenans: mövcud məqalələr üçün arXiv mənbə sətri
        conn.execute(text("""
            INSERT INTO paper_sources (paper_id, source, external_id, url)
            SELECT p.id, p.source, p.external_id, p.pdf_url
              FROM papers p
             WHERE p.external_id IS NOT NULL
               AND NOT EXISTS (
                   SELECT 1 FROM paper_sources s
                    WHERE s.source = p.source AND s.external_id = p.external_id
               )
        """))

    # title_key və language Python məntiqi tələb edir — yalnız boş olanlar üçün
    from .sources.common import detect_language, title_key

    with Session(engine) as db:
        rows = db.execute(
            text("SELECT id, title FROM papers WHERE title_key IS NULL LIMIT 20000")
        ).all()
        for row in rows:
            db.execute(
                text("UPDATE papers SET title_key = :k WHERE id = :i"),
                {"k": title_key(row.title), "i": row.id},
            )
        if rows:
            db.commit()
            log.info("title_key hesablandı: %s sətir", len(rows))

        lang_rows = db.execute(
            text("SELECT id, title, abstract FROM papers WHERE language IS NULL LIMIT 50000")
        ).all()
        for row in lang_rows:
            db.execute(
                text("UPDATE papers SET language = :l WHERE id = :i"),
                {"l": detect_language(row.title, row.abstract), "i": row.id},
            )
        if lang_rows:
            db.commit()
            log.info("language təyin edildi: %s sətir", len(lang_rows))
