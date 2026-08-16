from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Bütün konfiqurasiya bir yerdə — dəyərlər .env və mühit dəyişənlərindən gəlir."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Bağlantı komponentləri ayrıca saxlanılır və URL SQLAlchemy tərəfindən qurulur.
    # Parolu URL sətrinə əl ilə yapışdırmaq təhlükəlidir: içindəki `@`, `/`, `:` kimi
    # simvollar sətri sındırır (məs. `@` olanda host `@postgres` kimi oxunur və
    # Linux bunu abstrakt Unix socket sayır — bağlantı heç cəhd edilmir).
    postgres_user: str = "elmradari"
    postgres_password: str = "elmradari"
    postgres_db: str = "elmradari"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    # Açıq verilsə, komponentləri üstələyir (məs. xarici idarə olunan baza).
    database_url_override: str = ""

    redis_url: str = "redis://localhost:6379/0"

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        from sqlalchemy import URL

        return URL.create(
            "postgresql+psycopg2",
            username=self.postgres_user,
            password=self.postgres_password,   # xüsusi simvollar burada düzgün kodlanır
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        ).render_as_string(hide_password=False)

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Çoxdilli model: rus/Azərbaycan sorğusu ilə ingiliscə mətn arasında da
    # uyğunluq tapır (RU↔EN oxşarlıq testdə 0.79). Ölçü əvvəlki ilə eynidir (384),
    # ona görə baza sxemi dəyişmir — yalnız yenidən embed etmək lazımdır.
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = 384
    hf_cache_dir: str = "/models"

    # Crossref/DOAJ «nəzakətli hovuz» üçün əlaqə e-poçtu (boş qala bilər)
    contact_email: str = ""

    # --- İctimai deploy qorumaları ---
    public_mode: bool = False        # True: yazma endpoint-ləri açar tələb edir, limitlər işləyir
    admin_api_key: str = ""          # n8n və admin əməliyyatları üçün paylaşılan sirr
    trust_proxy: bool = False        # reverse proxy arxasındasa X-Forwarded-For oxunsun
    ask_rate_limit: int = 20         # IP üzrə saatlıq LLM sualı
    ask_daily_budget: int = 500      # bütün istifadəçilər üçün günlük LLM tavanı
    search_rate_limit: int = 120     # IP üzrə saatlıq semantik axtarış
    # Tərcümə də LLM çağırışıdır: az/ru axtarış Groq-a gedir. /api/ask-ın günlük
    # tavanı bunu tutmurdu — audit S3. Aşılanda tərcümə dayanır, axtarış işləməyə
    # davam edir (xəta yox, degrade).
    translate_daily_budget: int = 2000

    # §18: provider seçimi konfiqurasiyadan gəlir, koddan yox.
    llm_provider: str = "groq"
    embedding_provider: str = "fastembed"
    # Boş = rerank sönülüdür. §5: yalnız ölçmə fayda göstərəndən sonra açılır.
    rerank_provider: str = ""
    # Çoxdilli seçildi: ms-marco yalnız ingiliscədir və korpusun rusdilli
    # hissəsində mənasız işləyərdi (embedding modelində eyni səhvi bir dəfə
    # etmişdik və düzəltmək bütün korpusun yenidən hesablanmasına baş verdi).
    rerank_model: str = "BAAI/bge-reranker-base"
    # Rerank namizəd hovuzu: nə qədər böyükdürsə, o qədər çox şans, o qədər baha
    rerank_pool: int = 30

    # Çıxarış (§7) üçün AYRICA model. Cavab keyfiyyəti kritikdir və 70B işlədilir,
    # amma struktur çıxarış minlərlə məqalə üçün təkrarlanan mexaniki işdir:
    # ölçüldü — 70B ilə 300 məqalədən yalnız 11-i alındı, qalanı rate limit-ə
    # dirəndi. Kiçik model bu işi görür və limiti qat-qat gec doldurur.
    extract_model: str = "llama-3.1-8b-instant"

    # Retrieval üsulu: "vector" | "lexical" | "hybrid".
    #
    # ÖLÇÜLDÜ, "vector" SEÇİLDİ (korpus 1596, n=60, 28 eval sorğusu):
    #
    #            P@10 az   P@10 en   P@10 ru   gecikmə
    #   vector      68%       63%       62%      61 ms
    #   lexical     40%       75%      100%*      5 ms
    #   hybrid      65%       65%       63%      64 ms
    #
    # Hibridin təsiri: az -3%, en +2%, ru +2% → orta +0.3%, yəni səs-küy.
    # Leksikin ru=100% rəqəmi artefaktdır: rusca sorğu sv_ru-ya gedir və
    # ingiliscə məqalələrdə rus kökləri yoxdur, ona görə yalnız rusdilli
    # nəticələr qayıda bilər — bu, məhsul üçün pisdir (ingiliscə korpus
    # görünməz olur), yaxşı deyil.
    #
    # Kod saxlanılır (test olunub, xərci yoxdur), rejim isə ölçmə fayda
    # göstərənə qədər "vector" qalır — §5.
    retrieval_mode: str = "vector"

    chunk_size: int = 1200
    chunk_overlap: int = 150

    ask_cache_ttl: int = 86400        # 24 saat
    analytics_cache_ttl: int = 21600  # 6 saat

    # --- Hesab qatı ---
    # Axtarış və məqalə səhifələri hesabsız görünür. Bu, qəsdəndir: qazanma
    # kanalı və SEO buradan gəlir, rəqib (ChatGPT) isə qapı qoymur. Bağlanan
    # şey qapı deyil, İMKANdır — sual, saxlama və PDF hesab tələb edir.
    # False edilsə bütün /api yolları girişlə qorunur (tam bağlı platforma).
    public_browse: bool = True
    session_ttl_days: int = 30
    # Cookie yalnız HTTPS üzərindən getsin. Lokal işdə (http://localhost)
    # False olmalıdır, əks halda brauzer cookie-ni saxlamır və giriş "işləmir".
    session_cookie_secure: bool = True
    # Qeydiyyat/giriş sui-istifadəsi: IP üzrə saatlıq
    signup_rate_limit: int = 5
    login_rate_limit: int = 10
    # Parol minimumu. NIST tövsiyəsi: uzunluq mürəkkəblikdən vacibdir.
    min_password_length: int = 10

    # --- Plan və kredit ---
    # Kredit = bahalı əməliyyatların vahid ölçüsü. Xam token göstərmirik (§19):
    # istifadəçi "500 tədqiqat krediti" görür, API paneli yox.
    # Kredit sayı qiymətə görə seçilib, təsadüfi deyil. Pro $5/ay; Paddle
    # komissiyası (~5% + $0.50 sabit) çıxandan sonra ~$4.25 qalır. Sualbaşına
    # Groq xərci ~$0.002 olduğuna görə 1000 kredit tam işlənsə ~$2.30 tutur —
    # yəni ən fəal istifadəçidə belə marja müsbətdir.
    # Bu rəqəmi qaldırmazdan əvvəl `usage_events` cədvəlindən real orta xərci
    # ölç; təxminlə deyil, dəftərlə dəyişdirilməlidir.
    free_monthly_credits: int = 60
    pro_monthly_credits: int = 1000
    free_library_limit: int = 10
    pro_library_limit: int = 5000

    # --- Ödəniş ---
    # "paddle" | "" (sönülü). Stripe Azərbaycanda satıcı hesabı açmır, ona görə
    # Merchant of Record seçildi: ƏDV/vergi öhdəliyi provayderin üzərindədir.
    payment_provider: str = ""
    # Server tərəfli, GİZLİ. Hazırda işlənmir (checkout brauzerdə açılır,
    # webhook isə ayrı sirrlə yoxlanılır) — abunə idarəetməsi əlavə olunanda
    # lazım olacaq.
    paddle_api_key: str = ""
    # Brauzerə düşür və gizli DEYİL — Paddle.js checkout-u bununla açılır.
    # API açarı ilə qarışdırılmamalıdır: onu frontend-ə vermək bütün hesaba
    # giriş verməkdir.
    paddle_client_token: str = ""
    paddle_webhook_secret: str = ""
    paddle_price_id_pro: str = ""
    paddle_environment: str = "sandbox"     # sandbox | production
    # Checkout-dan qayıdış üçün. Boş qalsa sorğunun öz host-u işlədilir.
    public_base_url: str = ""


settings = Settings()
