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
    pmid: str | None = Field(default=None, max_length=MAX_ID)
    openalex_id: str | None = Field(default=None, max_length=MAX_ID)
    primary_category: str | None = Field(default=None, max_length=64)
    categories: list[str] = Field(default=[], max_length=64)
    field_keys: list[str] = Field(default=[], max_length=32)
    authors: list[str] = Field(default=[], max_length=500)
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
            self.external_id = self.arxiv_id or self.doi or self.pmid or self.openalex_id
        if self.source == "arxiv" and not self.arxiv_id and self.external_id:
            self.arxiv_id = self.external_id
        if not self.external_id:
            raise ValueError(
                "identifikator tələb olunur: external_id, arxiv_id, doi, pmid və ya openalex_id"
            )
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


class QueryPlanOut(BaseModel):
    """Sorğudan çıxarılan niyyət və məhdudiyyətlər (§6).

    İnterfeys buna görə uyğun imkanı təklif edir: «bu, müqayisə sualına
    oxşayır — seçdiyin məqalələri müqayisə edim?» Beləliklə əsas axın sadə
    qalır, qabaqcıl funksiyalar isə görünən olur (§19).
    """
    intent: str = "SEARCH"
    intents: list[str] = []
    suggested_endpoint: str | None = None
    authors: list[str] = []
    year_from: int | None = None
    year_to: int | None = None
    # Məhdudiyyətlər çıxarıldıqdan sonra faktiki axtarılan mətn
    core: str = ""


class SearchResponse(BaseModel):
    query: str
    lang: str
    query_en: str | None = None  # az/ru sorğunun ingiliscə tərcüməsi
    hits: list[SearchHit]
    plan: QueryPlanOut | None = None


# ---------- Ask (RAG) ----------

class ChatTurn(BaseModel):
    """Söhbətin bir növbəsi. Tarixçə istifadəçidən gəlir, ona görə həm rol,
    həm uzunluq məhdudlaşdırılır — əks halda ixtiyari «assistant» mesajı
    göndərib modelin davranışını dəyişmək mümkün olardı."""

    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=2000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    top_k: int = Field(5, ge=1, le=10)
    # Ağ siyahı `ask.py`-dədir (FIELDS). Buradakı hədd yalnız uzun dəyərin
    # xəta mesajında GERİ ƏKS OLUNMASININ qarşısını alır.
    field: str | None = Field(default=None, max_length=64)
    # Söhbətin davam etməsi üçün. Son 6 növbə saxlanılır (llm._clean_history).
    history: list[ChatTurn] = Field(default=[], max_length=20)


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


class GroundingOut(BaseModel):
    """Cavabın sübutla əlaqəsi (§8, §20).

    İstifadəçi üçün deyil, ŞƏFFAFLIQ üçün: cavabın nə qədər sübutla dayandığı
    və LLM-in uydurduğu istinadın olub-olmadığı ölçülə bilən olmalıdır.
    """
    evidence_used: int          # LLM-ə verilən sənəd sayı
    evidence_dropped: int       # həddi keçmədiyi üçün atılan
    top_score: float            # ən güclü sübutun oxşarlığı
    weak: bool                  # ən yaxşı sübut da zəifdirsə
    citations_valid: int        # kontekstdə həqiqətən olan istinadlar
    citations_removed: list[str] = []   # LLM-in uydurduğu və silinən istinadlar
    coverage: float = 0.0       # istifadə olunan sübutun neçə faizinə istinad edilib


class CorpusOut(BaseModel):
    """Cavabın əsaslandığı korpus (§16).

    "Bu təhlil indekslənmiş korpusa əsaslanır" mesajını RƏQƏMLƏ dəstəkləyir —
    istifadəçi əhatənin sərhədini görməlidir, sistem isə heç vaxt bütün elmi
    ədəbiyyatı təmsil etdiyini ima etməməlidir.
    """
    papers: int
    sources: list[str] = []
    languages: list[str] = []
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceOut]
    from_cache: bool
    latency_ms: int
    query_en: str | None = None
    grounding: GroundingOut | None = None
    corpus: CorpusOut | None = None
    # Cavabdan sonra qalan kredit — interfeys əlavə sorğu atmadan göstərsin.
    credits_left: int | None = None


# ---------- Hesab ----------

class RegisterRequest(BaseModel):
    # Parol uzunluğu burada YOXLANMIR — qayda `auth.password_problem()`-dədir
    # ki, mesaj bir yerdən gəlsin və konfiqurasiya ilə dəyişə bilsin.
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)
    display_name: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)


class PlanOut(BaseModel):
    key: str
    label: str
    monthly_credits: int
    library_limit: int
    capabilities: list[str]
    features: list[str] = []


class UserOut(BaseModel):
    """Cavabda `password_hash` və sessiya tokeni HEÇ VAXT olmur —
    modeli birbaşa qaytarmaq əvəzinə açıq sahə siyahısı saxlanılır."""

    id: int
    email: str
    display_name: str | None = None
    plan: str
    plan_label: str
    credits_left: int
    credits_total: int
    library_used: int
    library_limit: int
    capabilities: list[str] = []
    subscription_status: str | None = None
    plan_expires_at: datetime | None = None
    created_at: datetime


class SavePaperRequest(BaseModel):
    paper_id: int = Field(ge=1)
    note: str | None = Field(default=None, max_length=2000)


class PaperStateIn(BaseModel):
    """Vəziyyət yaması: yalnız GÖNDƏRİLƏN sahələr dəyişir.

    `None` «dəymə» deməkdir, `False` isə «sil». Bu fərq vacibdir — əks
    halda ulduzu dəyişmək istəyən sorğu, göndərmədiyi `saved` sahəsini
    də təsadüfən sıfırlayardı.
    """

    saved: bool | None = None
    starred: bool | None = None
    read: bool | None = None
    note: str | None = Field(default=None, max_length=2000)


class PaperStateOut(BaseModel):
    paper_id: int
    saved: bool = False
    starred: bool = False
    read: bool = False
    read_at: datetime | None = None


class LibraryStateOut(BaseModel):
    """Bütün kitabxananın vəziyyəti — yalnız ID-lər.

    İnterfeys axtarış nəticələrindəki hər kartın ulduzlu/saxlanmış/oxunmuş
    olduğunu bilməlidir. Hər kart üçün ayrıca sorğu atmaq onlarla sorğu
    demək idi; tam məqalə obyektlərini qaytarmaq isə lazımsız yükdür.
    Ona görə yalnız ID çoxluqları gedir və interfeys onları yerli saxlayır.
    """

    saved: list[int] = []
    starred: list[int] = []
    read: list[int] = []


class SavedPaperOut(BaseModel):
    paper: PaperOut
    note: str | None = None
    created_at: datetime
    starred: bool = False
    read_at: datetime | None = None


class UsageOut(BaseModel):
    action: str
    credits: int
    created_at: datetime


class CheckoutOut(BaseModel):
    """Paddle checkout-u frontend-də açılır, ona görə URL yox, parametrlər.

    Burada YALNIZ brauzerə düşməsi təhlükəsiz olan dəyərlər var. Server tərəfli
    API açarı bu modelə heç vaxt əlavə edilməməlidir.
    """

    provider: str
    environment: str
    client_token: str
    price_id: str
    customer_email: str
    custom_data: dict[str, str]
    return_url: str


# ---------- Şəxsi sənədlər (PDF) ----------

class DocumentOut(BaseModel):
    """`status` interfeys üçün vacibdir: emal fonda gedir və istifadəçi
    «hazırlanır» / «hazır» / «alınmadı» fərqini görməlidir."""

    id: int
    filename: str
    title: str | None = None
    pages: int = 0
    chunk_count: int = 0
    status: str = "processing"
    error: str | None = None
    created_at: datetime


class DocumentAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    top_k: int = Field(6, ge=1, le=12)
    history: list[ChatTurn] = Field(default=[], max_length=20)


class DocumentSourceOut(BaseModel):
    """İstinad SƏHİFƏ ilə verilir — «Sənəd → Səhifə → Parça».

    Sübutun yoxlanıla bilməsi məhz buradan gəlir: istifadəçi PDF-i açıb həmin
    səhifəyə baxa bilir.
    """
    page: int
    score: float
    excerpt: str


class DocumentAskResponse(BaseModel):
    answer: str
    document: dict
    sources: list[DocumentSourceOut] = []
    grounding: GroundingOut | None = None
    latency_ms: int
    credits_left: int | None = None


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
    content: str = Field(max_length=200_000)


class DigestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    week_start: date
    content: str
    created_at: datetime


class ErrorIn(BaseModel):
    workflow: str = Field(max_length=200)
    node: str | None = None
    message: str = Field(max_length=20_000)


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
