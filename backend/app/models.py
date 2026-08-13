from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import UniqueConstraint

from .config import settings
from .database import Base

paper_authors = Table(
    "paper_authors",
    Base.metadata,
    Column("paper_id", ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
    Column("author_id", ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
)

paper_categories = Table(
    "paper_categories",
    Base.metadata,
    Column("paper_id", ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
    Column("category_code", ForeignKey("categories.code", ondelete="CASCADE"), primary_key=True),
)


class Paper(Base):
    """Bir elmi iş — mənbədən asılı olmayaraq TƏK sətir.

    Eyni iş arXiv-də preprint, Crossref-də DOI-lu nəşr kimi görünə bilər;
    hamısı bu sətrə bağlanır, əlavə mənbələr `sources` əlaqəsində saxlanılır.
    """

    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(Text, index=True, default="arxiv")   # ilk görüldüyü mənbə
    external_id: Mapped[str | None] = mapped_column(Text, index=True)
    arxiv_id: Mapped[str | None] = mapped_column(Text, unique=True, index=True)
    doi: Mapped[str | None] = mapped_column(Text, index=True)
    pmid: Mapped[str | None] = mapped_column(Text, index=True)               # PubMed/Europe PMC
    openalex_id: Mapped[str | None] = mapped_column(Text, index=True)        # W-prefiksli OpenAlex work id
    title_key: Mapped[str | None] = mapped_column(Text, index=True)          # dedup üçün normallaşdırılmış başlıq
    language: Mapped[str] = mapped_column(Text, index=True, default="en")    # mətnin əlifbasından təyin olunur
    title: Mapped[str] = mapped_column(Text)
    abstract: Mapped[str] = mapped_column(Text)
    primary_category: Mapped[str | None] = mapped_column(Text, index=True)
    field_keys = mapped_column(ARRAY(Text), default=list)                    # 8 sahədən hansılara aiddir
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    # Leksik axtarış üçün (Phase 2). Postgres özü hesablayır və saxlayır —
    # abstrakt zənginləşəndə (D6) indeks avtomatik yenilənir, kod sinxronlaşdırmır.
    # İki ayrı sütun, çünki to_tsvector yalnız SABİT konfiqurasiya ilə IMMUTABLE-dir.
    sv_en = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
            "setweight(to_tsvector('english', coalesce(abstract, '')), 'B')",
            persisted=True,
        ),
        nullable=True,
    )
    sv_ru = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('russian', coalesce(title, '')), 'A') || "
            "setweight(to_tsvector('russian', coalesce(abstract, '')), 'B')",
            persisted=True,
        ),
        nullable=True,
    )
    pdf_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    authors: Mapped[list["Author"]] = relationship(secondary=paper_authors, back_populates="papers")
    categories: Mapped[list["Category"]] = relationship(secondary=paper_categories, back_populates="papers")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    sources: Mapped[list["PaperSource"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan"
    )


class PaperSource(Base):
    """Provenans: məqalənin hansı mənbələrdə görüldüyü (dublikat birləşəndə artır)."""

    __tablename__ = "paper_sources"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_source_external"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(Text, index=True)
    external_id: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    paper: Mapped[Paper] = relationship(back_populates="sources")


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True)

    papers: Mapped[list[Paper]] = relationship(secondary=paper_authors, back_populates="authors")


class Category(Base):
    __tablename__ = "categories"

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text)

    papers: Mapped[list[Paper]] = relationship(secondary=paper_categories, back_populates="categories")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(settings.embedding_dim))
    # Vektoru hansı modelin hesabladığı — model dəyişəndə yenidən embed
    # olunmalı sətirlər buradan tapılır (proses kəsilsə davam etdirmək üçün).
    embedding_model: Mapped[str | None] = mapped_column(Text, index=True)

    paper: Mapped[Paper] = relationship(back_populates="chunks")


class PaperInsight(Base):
    """Məqalə səviyyəli çıxarış — §7.

    Niyə JSONB, niyə 12 ayrı sütun deyil: §7 hər sahə üçün yalnız DƏYƏRİ yox,
    həm də SÜBUT TİPİNİ tələb edir (stated / synthesized / inferred) və dəyəri
    dayaqlayan sitatı. Bu, sahə başına üç sütun demək olardı. JSONB struktur
    dəyişəndə miqrasiya tələb etmir və axtarış GIN indeksi ilə işləyir.

    `model` sütunu vacibdir: çıxarış LLM-dən gəlir, model dəyişəndə hansı
    sətirlərin yenidən hesablanmalı olduğu buradan bilinir (chunk-lardakı
    `embedding_model` ilə eyni məntiq).
    """

    __tablename__ = "paper_insights"

    paper_id: Mapped[int] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True
    )
    data = mapped_column(JSONB, default=dict)
    model: Mapped[str | None] = mapped_column(Text, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    paper: Mapped[Paper] = relationship()


class QaHistory(Base):
    __tablename__ = "qa_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    sources = mapped_column(JSONB, default=list)
    from_cache: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IngestRun(Base):
    __tablename__ = "ingest_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fetched: Mapped[int] = mapped_column(Integer, default=0)
    inserted: Mapped[int] = mapped_column(Integer, default=0)
    skipped: Mapped[int] = mapped_column(Integer, default=0)
    merged: Mapped[int] = mapped_column(Integer, default=0)   # başqa mənbədə tapılıb birləşdirilən
    source: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="success")


class ErrorLog(Base):
    __tablename__ = "error_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow: Mapped[str] = mapped_column(Text)
    node: Mapped[str | None] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text)
    happened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Digest(Base):
    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(primary_key=True)
    week_start: Mapped[date] = mapped_column(Date, unique=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
