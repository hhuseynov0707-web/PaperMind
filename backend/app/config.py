from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Bütün konfiqurasiya bir yerdə — dəyərlər .env və mühit dəyişənlərindən gəlir."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://elmradari:elmradari@localhost:5433/elmradari"
    redis_url: str = "redis://localhost:6379/0"

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
