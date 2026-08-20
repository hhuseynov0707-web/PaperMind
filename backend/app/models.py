from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    Computed,
    Date,
    DateTime,
    Float,
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


class PaperRelation(Base):
    """Məqalələr arası əlaqə — §15.

    Ayrıca graph DB QURULMADI. §15 açıq deyir: *«Do not introduce a separate
    graph database unless the existing architecture genuinely requires it»*.
    Korpus ~1 600 məqalədir; belə ölçüdə iki indeksli cədvəl bütün keçid
    sorğularını millisaniyələrlə cavablandırır.

    `confidence` və `evidence` vacibdir, çünki əlaqələrin mənbəyi fərqlidir:
    `cites` OpenAlex-in `referenced_works` sahəsindən gəlir və FAKTdır (1.0);
    `contradicts` isə LLM qiymətləndirməsindən gəlir və şübhəlidir. Onları eyni
    cədvəldə saxlayıb eyni etibarla göstərmək yanlış olardı.
    """

    __tablename__ = "paper_relations"
    __table_args__ = (
        UniqueConstraint("from_paper_id", "to_paper_id", "relation", name="uq_relation"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    from_paper_id: Mapped[int] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), index=True
    )
    to_paper_id: Mapped[int] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), index=True
    )
    relation: Mapped[str] = mapped_column(Text, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    evidence: Mapped[str | None] = mapped_column(Text)      # nəyə əsasən
    source: Mapped[str | None] = mapped_column(Text)        # openalex | llm | derived
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


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


class User(Base):
    """Platforma istifadəçisi.

    `plan` burada saxlanılır, ayrıca `subscriptions` cədvəlində yox: sorğu başına
    plan oxunur və bir JOIN-dən qaçmaq bu qədər tez-tez oxunan sahə üçün dəyər.
    Abunənin tarixçəsi lazım olanda `usage_events` və provayderin öz paneli var.

    Kreditlər `credits_period` (YYYYMM) ilə birlikdə saxlanılır — ay dəyişəndə
    sayğac oxunuş anında sıfırlanır, yəni ayın əvvəlində cron işlətmək lazım
    deyil. Cron olsaydı, işləməyəndə istifadəçi səssizcə bloklanardı.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Aşağı registrdə saxlanılır — «Ali@x.com» və «ali@x.com» eyni hesabdır
    email: Mapped[str] = mapped_column(Text, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(Text)
    plan: Mapped[str] = mapped_column(Text, default="free", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    credits_used: Mapped[int] = mapped_column(Integer, default=0)
    credits_period: Mapped[str | None] = mapped_column(Text)      # YYYYMM

    # Provayderdəki abunə (Paddle). Plan dəyişikliyi yalnız webhook-dan gəlir.
    billing_customer_id: Mapped[str | None] = mapped_column(Text, index=True)
    subscription_id: Mapped[str | None] = mapped_column(Text, index=True)
    subscription_status: Mapped[str | None] = mapped_column(Text)
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Silinmə TƏLƏBİ. Sətir dərhal silinmir: istifadəçiyə fikrini dəyişmək
    # üçün möhlət verilir (§GDPR — «unudulma hüququ», amma təsadüfi klik
    # geri qaytarıla bilməlidir). Möhlət bitəndə `purge` sətri həqiqətən silir.
    deletion_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSession(Base):
    """Sessiya — opak token, JWT yox.

    Səbəb: JWT-ni vaxtından əvvəl ləğv etmək olmur. Bizdə çıxış, plan dəyişikliyi
    və hesabın bloklanması DƏRHAL təsir etməlidir. Üstəlik hər sorğuda plan və
    kredit onsuz da bazadan oxunur, yəni JWT-nin «bazaya getmə» üstünlüyü burada
    yoxdur.

    Tokenin ÖZÜ saxlanılmır, yalnız SHA-256 həshi: baza sızsa belə, oğurlanmış
    sətirlərlə sessiya bərpa etmək mümkün olmasın (parol həshi ilə eyni məntiq).
    """

    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(Text, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    user_agent: Mapped[str | None] = mapped_column(Text)
    ip: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="sessions")


class SavedPaper(Base):
    """İstifadəçi ilə məqalə arasındakı MÜNASİBƏT — «research memory»nin ilk daşı.

    Üç vəziyyət var və hamısı BİR sətirdədir: oxu siyahısında (`saved`),
    ulduzlanmış (`starred`), oxunmuş (`read_at`). Ayrı-ayrı cədvəllər
    qurmadıq, çünki üçü də eyni (istifadəçi, məqalə) cütünə aiddir —
    üç cədvəl olsaydı, bir kartın vəziyyətini bilmək üçün üç sorğu
    lazım gələrdi və onları sinxron saxlamaq bizim üzərimizə düşərdi.

    Sətir vəziyyətlərdən heç biri qalmayanda silinir (bax: `_prune`),
    yoxsa cədvəl heç nə ifadə etməyən boş sətirlərlə dolar.
    """

    __tablename__ = "saved_papers"
    __table_args__ = (UniqueConstraint("user_id", "paper_id", name="uq_saved_user_paper"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True)
    note: Mapped[str | None] = mapped_column(Text)

    # Mövcud sətirlərin hamısı «saxlanmış»dır, ona görə default true —
    # miqrasiya köhnə kitabxananı olduğu kimi saxlayır.
    saved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    starred: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    # Vaxt saxlanılır, sadəcə bayraq yox: «oxundu tarixçəsi» sıralanmalıdır.
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    paper: Mapped[Paper] = relationship()


class UsageEvent(Base):
    """Kredit hərəkətlərinin dəftəri.

    `users.credits_used` cari vəziyyəti saxlayır, bu cədvəl isə NİYƏ-ni: hansı
    əməliyyat neçə kredit yandırdı. Mübahisə olanda («kreditim niyə bitdi?»)
    cavab verə bilmək üçün lazımdır, həm də hansı əməliyyatın bahalı olduğunu
    ölçmək bu dəftər olmadan mümkün deyil.
    """

    __tablename__ = "usage_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(Text, index=True)
    credits: Mapped[int] = mapped_column(Integer, default=0)
    meta = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class BillingEvent(Base):
    """Provayderdən gələn webhook-ların qeydi — idempotentlik üçün.

    Ödəniş provayderləri eyni hadisəni TƏKRAR göndərir (şəbəkə xətası, retry).
    `event_id` unikal olduğu üçün ikinci dəfə gələn hadisə emal edilmir —
    əks halda bir ödənişə görə plan iki dəfə uzadıla bilərdi.
    """

    __tablename__ = "billing_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(Text, unique=True, index=True)
    event_type: Mapped[str] = mapped_column(Text, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    payload = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Document(Base):
    """İstifadəçinin yüklədiyi PDF.

    `digest` (SHA-256) unikaldır İSTİFADƏÇİ ÜZRƏ: eyni faylı təkrar yükləmək
    yeni sənəd yaratmır, mövcudu qaytarır. Qlobal unikal olsaydı, iki fərqli
    istifadəçi eyni məqaləni yükləyəndə biri digərinin sənədini görərdi.

    `status` lazımdır, çünki emal (mətn çıxarma + embedding) yükləmə sorğusundan
    uzun çəkir və fonda gedir. İstifadəçi «hazırlanır» vəziyyətini görməlidir,
    boş siyahı yox.
    """

    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("user_id", "digest", name="uq_user_document"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    digest: Mapped[str] = mapped_column(Text, index=True)
    pages: Mapped[int] = mapped_column(Integer, default=0)
    chars: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(Text, default="processing", index=True)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    """Sənədin bir parçası — səhifə nömrəsi ilə.

    HNSW indeksi QURULMUR, `chunks` cədvəlindən fərqli olaraq. Səbəb: axtarış
    həmişə BİR sənədin içindədir (`document_id` filtri), orada isə bir neçə yüz
    sətir olur. Belə ölçüdə ardıcıl oxuma HNSW-dən sürətlidir və indeks yalnız
    yazma xərci və yaddaş əlavə edərdi. Bütün sənədlər üzrə axtarış (Pro-nun
    «kitabxana üzrə sintez» funksiyası) əlavə olunanda bu qərar yenidən
    ölçülməlidir.
    """

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    page: Mapped[int] = mapped_column(Integer)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(settings.embedding_dim))
    embedding_model: Mapped[str | None] = mapped_column(Text)

    document: Mapped[Document] = relationship(back_populates="chunks")


class Digest(Base):
    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(primary_key=True)
    week_start: Mapped[date] = mapped_column(Date, unique=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
