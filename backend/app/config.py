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

    chunk_size: int = 1200
    chunk_overlap: int = 150

    ask_cache_ttl: int = 86400        # 24 saat
    analytics_cache_ttl: int = 21600  # 6 saat


settings = Settings()
