from datetime import date, datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

# ---------- Giriş həddi (§17: oversized documents) ----------
# Bir yerdə saxlanılır ki, testlər və validasiya eyni rəqəmə baxsın.
MAX_TITLE = 1_000
MAX_ABSTRACT = 50_000      # real korpusda ən uzunu ~8 000
MAX_ID = 256
MAX_URL = 2_000
MAX_ITEM = 300             # bir müəllif adı / kateqoriya kodu
MAX_AUTHORS = 200          # fizikada 3000+ müəllifli məqalələr var → kəsilir, rədd edilmir
MAX_CATEGORIES = 50
MAX_BATCH = 500            # bir ingest sorğusunda məqalə sayı

LIST_CAPS = {"authors": MAX_AUTHORS, "categories": MAX_CATEGORIES, "field_keys": MAX_CATEGORIES}


# ---------- Ingest ----------

class PaperIn(BaseModel):
    """Bir mənbədən gələn məqalə.

    Köhnə n8n workflow-ları yalnız `arxiv_id` göndərir — `source`/`external_id`
    verilməyəndə onlar arxiv_id-dən çıxarılır (geriyə uyğunluq).
    """

    # Limitlər sərtdir, çünki bu model xarici mənbələrdən gələn və istifadəçinin
    # göndərə bildiyi datanı qəbul edir. Limitsiz abstract chunker-i və embedding-i
    # partladır (bir sətir minlərlə chunk = CPU + yaddaş + xərc).
    # Ölçülər real korpusa görə seçilib: ən uzun abstract ~8 000 simvoldur.
    title: str = Field(min_length=1, max_length=MAX_TITLE)
    abstract: str = Field(max_length=MAX_ABSTRACT)
    source: str = Field(default="arxiv", max_length=32)
    external_id: str | None = Field(default=None, max_length=MAX_ID)
    arxiv_id: str | None = Field(default=None, max_length=MAX_ID)
    doi: str | None = Field(default=None, max_length=MAX_ID)
    primary_category: str | None = Field(default=None, max_length=64)
    categories: list[str] = []
    field_keys: list[str] = []
    authors: list[str] = []
    published_at: datetime | None = None
    pdf_url: str | None = Field(default=None, max_length=MAX_URL)
    language: str | None = Field(default=None, max_length=8)  # verilməsə mətndən təyin olunur

    @field_validator("authors", "categories", "field_keys", mode="before")
    @classmethod
    def _bound_list(cls, values, info: ValidationInfo):
        """Siyahılar RƏDD EDİLMİR, KƏSİLİR.

        Səbəb: fizikada (CERN kollaborasiyaları) 3 000+ müəllifli real məqalələr
        var. `max_length` ilə rədd etsək həmin məqalələri tamamilə itirərdik —
        halbuki məqsəd yaddaşı məhdudlaşdırmaqdır, məqaləni atmaq yox.
        Eyni məntiq element uzunluğuna da aiddir: 10 MB-lıq "müəllif adı"
        onsuz da zibildir, kəsilməsi bütöv məqaləni itirməkdən yaxşıdır.
        """
        if not isinstance(values, list):
            return values
        cap = LIST_CAPS.get(info.field_name, MAX_CATEGORIES)
        return [str(v)[:MAX_ITEM] for v in values[:cap]]

    @model_validator(mode="after")
    def _fill_identity(self):
        if not self.external_id:
            self.external_id = self.arxiv_id or self.doi
        if self.source == "arxiv" and not self.arxiv_id and self.external_id:
            self.arxiv_id = self.external_id
        if not self.external_id:
            raise ValueError("external_id, arxiv_id və ya doi-dən biri tələb olunur")
        return self


class IngestBatch(BaseModel):
    # Partiya limiti: bir sorğu bütün embedding gücünü tutmasın
    papers: list[PaperIn] = Field(max_length=MAX_BATCH)


class IngestResult(BaseModel):
    received: int
    inserted: int
    skipped: int
    merged: int = 0


class PullRequest(BaseModel):
    """Server tərəfli yığım: n8n bunu çağırır, parsing Python-da qalır."""

    source: str
    fields: list[str] = []          # boşdursa hamısı
    days: int = Field(3, ge=1, le=60)
    limit_per_field: int = Field(60, ge=1, le=400)
    lang: str = Field("en", pattern="^(en|ru)$")   # hansı dildə məqalə axtarılsın


class PullResult(BaseModel):
    source: str
    fetched: int
    inserted: int
    skipped: int
    merged: int
    per_field: dict[str, int] = {}


# ---------- Papers / Search ----------

class PaperOut(BaseModel):
    id: int
    arxiv_id: str | None
    doi: str | None = None
    title: str
    abstract: str
    primary_category: str | None
    published_at: datetime | None
    pdf_url: str | None
    language: str = "en"
    authors: list[str] = []
    categories: list[str] = []
    field_keys: list[str] = []
    sources: list[str] = []          # eyni işin tapıldığı bütün mənbələr


class PapersPage(BaseModel):
    items: list[PaperOut]
    total: int
    page: int
    page_size: int


class SearchHit(BaseModel):
    paper: PaperOut
    score: float


class SearchResponse(BaseModel):
    query: str
    lang: str
    query_en: str | None = None  # az/ru sorğunun ingiliscə tərcüməsi
    hits: list[SearchHit]


# ---------- Ask (RAG) ----------

class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    top_k: int = Field(5, ge=1, le=10)
    field: str | None = None  # sahə açarı (fields.FIELDS) — axtarışı daraldır


class FieldOut(BaseModel):
    key: str
    count: int
    group: str = ""             # təbiət elmləri, formal elmlər, ... (iyerarxik seçici üçün)
    categories: list[str] = []  # frontend kateqoriya -> sahə xəritəsini buradan qurur


class ServiceHealth(BaseModel):
    """Sistem statusu — yalnız real yoxlanıla bilən siqnallar."""

    postgres: bool
    pgvector: bool
    redis: bool
    groq_configured: bool
    last_ingest_at: datetime | None = None
    last_ingest_status: str | None = None


class SourceOut(BaseModel):
    # arXiv ID yalnız arXiv məqalələrində olur — Crossref/DOAJ/OpenAlex
    # qeydlərində DOI istinad rolunu oynayır. Məcburi saxlansaydı (əvvəl belə idi)
    # qeyri-arXiv mənbəyə istinad edən hər cavab 500 ilə çökərdi.
    arxiv_id: str | None = None
    doi: str | None = None
    title: str
    score: float
    pdf_url: str | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceOut]
    from_cache: bool
    latency_ms: int
    query_en: str | None = None


# ---------- Analytics ----------
# Qeyd: bu modellər Redis-dən JSON kimi qayıdır, ona görə tarixlər str saxlanılır.

class TrendPoint(BaseModel):
    week: str
    category: str
    count: int


class AuthorStat(BaseModel):
    name: str
    count: int


class CategoryCount(BaseModel):
    category: str
    count: int


class SourceCount(BaseModel):
    source: str
    count: int


class SummaryOut(BaseModel):
    total_papers: int
    total_chunks: int
    last_ingest: str | None
    by_category: list[CategoryCount]
    by_source: list[SourceCount] = []
    multi_source: int = 0          # birdən çox mənbədə tapılıb birləşdirilən


# ---------- Digest / Logs ----------

class DigestIn(BaseModel):
    week_start: date
    content: str


class DigestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    week_start: date
    content: str
    created_at: datetime


class ErrorIn(BaseModel):
    workflow: str
    node: str | None = None
    message: str


class ErrorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow: str
    node: str | None
    message: str
    happened_at: datetime


class IngestRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_at: datetime
    fetched: int
    inserted: int
    skipped: int
    merged: int = 0
    source: str | None = None
    status: str


class QaItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question: str
    from_cache: bool
    latency_ms: int
    created_at: datetime
