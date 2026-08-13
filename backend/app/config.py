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


settings = Settings()
