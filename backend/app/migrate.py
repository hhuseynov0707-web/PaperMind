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
    # §4: DOI və arXiv ID-dən əlavə kanonik identifikatorlar. PMID tibb/biologiya
    # üçün əsas açardır (Europe PMC/PubMed), OpenAlex ID isə çoxdilli korpusda
    # DOI-su olmayan işləri bağlayır.
    "ALTER TABLE papers ADD COLUMN IF NOT EXISTS pmid text",
    "ALTER TABLE papers ADD COLUMN IF NOT EXISTS openalex_id text",
    "CREATE INDEX IF NOT EXISTS ix_papers_pmid ON papers (pmid)",
    "CREATE INDEX IF NOT EXISTS ix_papers_openalex_id ON papers (openalex_id)",
    # §17: hesab silmə tələbi (GDPR). NULL = tələb yoxdur.
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS deletion_requested_at timestamptz",
    """CREATE INDEX IF NOT EXISTS ix_users_deletion ON users (deletion_requested_at)
           WHERE deletion_requested_at IS NOT NULL""",
    # §16: kitabxana vəziyyətləri — oxu siyahısı, ulduz, oxundu tarixçəsi.
    # Mövcud sətirlər saxlanmış məqalələrdir, ona görə `saved` DEFAULT true:
    # miqrasiya heç kimin kitabxanasını boşaltmır.
    "ALTER TABLE saved_papers ADD COLUMN IF NOT EXISTS saved boolean NOT NULL DEFAULT true",
    "ALTER TABLE saved_papers ADD COLUMN IF NOT EXISTS starred boolean NOT NULL DEFAULT false",
    "ALTER TABLE saved_papers ADD COLUMN IF NOT EXISTS read_at timestamptz",
    # Qismən indekslər: sorğular həmişə «bu istifadəçinin ulduzluları» və
    # «bu istifadəçinin oxuduqları» şəklindədir, bütün cədvəl deyil.
    """CREATE INDEX IF NOT EXISTS ix_saved_starred ON saved_papers (user_id)
           WHERE starred""",
    """CREATE INDEX IF NOT EXISTS ix_saved_read ON saved_papers (user_id, read_at DESC)
           WHERE read_at IS NOT NULL""",
    """CREATE INDEX IF NOT EXISTS ix_saved_list ON saved_papers (user_id, created_at DESC)
           WHERE saved""",
    # Phase 4 (§7): məqalə səviyyəli çıxarışlar
    """CREATE TABLE IF NOT EXISTS paper_insights (
           paper_id integer PRIMARY KEY REFERENCES papers(id) ON DELETE CASCADE,
           data jsonb DEFAULT '{}'::jsonb,
           model text,
           created_at timestamptz DEFAULT now()
       )""",
    "CREATE INDEX IF NOT EXISTS ix_insights_model ON paper_insights (model)",
    "CREATE INDEX IF NOT EXISTS ix_insights_data ON paper_insights USING gin (data)",
    # Phase 6 (§15): məqalələr arası əlaqələr. Graph DB YOX — Postgres kifayətdir.
    """CREATE TABLE IF NOT EXISTS paper_relations (
           id serial PRIMARY KEY,
           from_paper_id integer NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
           to_paper_id   integer NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
           relation text NOT NULL,
           confidence double precision DEFAULT 1.0,
           evidence text,
           source text,
           created_at timestamptz DEFAULT now(),
           CONSTRAINT uq_relation UNIQUE (from_paper_id, to_paper_id, relation)
       )""",
    "CREATE INDEX IF NOT EXISTS ix_rel_from ON paper_relations (from_paper_id)",
    "CREATE INDEX IF NOT EXISTS ix_rel_to ON paper_relations (to_paper_id)",
    "CREATE INDEX IF NOT EXISTS ix_rel_type ON paper_relations (relation)",
]

DOI_UNIQUE_INDEX = (
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_papers_doi ON papers (doi) WHERE doi IS NOT NULL"
)

# --- Phase 2: leksik axtarış (§5 hibrid retrieval) ---------------------------
#
# İki ayrı sütun, bir yox. Səbəb: `to_tsvector(config, text)` yalnız config
# SABİT olduqda IMMUTABLE-dir, ona görə sətrin `language` sütununa görə dinamik
# konfiqurasiya seçmək GENERATED sütunda mümkün deyil. Trigger yazmaq olardı,
# amma generated sütun kod tərəfindən sinxron saxlanmağa ehtiyac duymur —
# abstrakt zənginləşəndə (D6) indeks özü yenilənir.
#
# Praktikada bu, düzgün davranış da verir: rusca sorğu `sv_ru`-ya, ingiliscə
# sorğu `sv_en`-ə gedir. Rus stemmer-i ingiliscə mətndən mənasız token çıxarır,
# amma o tokenlər heç vaxt sorğulanmır.
#
# setweight: başlıq abstraktdan güclüdür (A > B) — known-item axtarışında
# başlıq uyğunluğu abstraktdakı təsadüfi termindən qat-qat mühümdür.
TSVECTOR_DDL = [
    """ALTER TABLE papers ADD COLUMN IF NOT EXISTS sv_en tsvector
       GENERATED ALWAYS AS (
           setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
           setweight(to_tsvector('english', coalesce(abstract, '')), 'B')
       ) STORED""",
    """ALTER TABLE papers ADD COLUMN IF NOT EXISTS sv_ru tsvector
       GENERATED ALWAYS AS (
           setweight(to_tsvector('russian', coalesce(title, '')), 'A') ||
           setweight(to_tsvector('russian', coalesce(abstract, '')), 'B')
       ) STORED""",
    "CREATE INDEX IF NOT EXISTS ix_papers_sv_en ON papers USING gin (sv_en)",
    "CREATE INDEX IF NOT EXISTS ix_papers_sv_ru ON papers USING gin (sv_ru)",
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

    # Leksik indeks (Phase 2). Ayrıca tranzaksiyada: GENERATED sütun əlavəsi
    # cədvəli yenidən yazır və köhnə Postgres versiyalarında dəstəklənmir —
    # uğursuz olsa sistem yalnız vektor axtarışı ilə işləməyə davam edir.
    try:
        with engine.begin() as conn:
            for stmt in TSVECTOR_DDL:
                conn.execute(text(stmt))
        log.info("Leksik indekslər (sv_en, sv_ru) hazırdır")
    except Exception as exc:
        log.warning("Leksik indeks qurula bilmədi (hibrid axtarış sönülü qalacaq): %s", exc)

    # DOI unikallığı (audit D3). Dedup yalnız tətbiq qatında idi — paralel ingest
    # eyni DOI-nu iki sətir kimi yaza bilərdi. Partial index, çünki DOI-suz
    # məqalələr (arXiv preprintləri) çoxdur və NULL-lar unikallıq pozmur.
    # Ayrıca tranzaksiyada: bazada artıq dublikat varsa bu addım uğursuz olur,
    # amma qalan miqrasiyanı dayandırmamalıdır.
    try:
        with engine.begin() as conn:
            conn.execute(text(DOI_UNIQUE_INDEX))
        log.info("DOI unikallıq indeksi hazırdır")
    except Exception as exc:
        log.warning(
            "DOI unikallıq indeksi yaradıla bilmədi — bazada təkrar DOI ola bilər: %s", exc
        )

    # Köhnə sətirlərin bərpası. DİQQƏT: bu blok əvvəllər səhvən `except`-in
    # içində idi — yəni HNSW uğurlu olanda HEÇ İŞLƏMİRDİ, uğursuz olanda isə
    # bağlanmış `conn` ilə çökürdü. İndi öz tranzaksiyasındadır.
    with engine.begin() as conn:
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
