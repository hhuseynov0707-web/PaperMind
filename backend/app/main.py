from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import cache, crud, migrate, models  # noqa: F401 — models: Base.metadata qeydiyyatı üçün
from .config import settings
from .database import Base, engine, get_db
from .routers import (
    accounts,
    analytics,
    ask,
    billing,
    digests,
    ingest,
    intelligence,
    library,
    logs,
    papers,
    search,
)
from .schemas import ServiceHealth


@asynccontextmanager
async def lifespan(app: FastAPI):
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)   # yeni cədvəllər (məs. paper_sources)
    migrate.run()                            # mövcud cədvəllərə sütun/indeks + backfill
    yield


app = FastAPI(
    title="PaperMind",
    description="Scientific Intelligence Platform — arXiv semantic search, source-grounded RAG and research trend analytics. FastAPI + PostgreSQL(pgvector) + Redis + n8n + Groq.",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@app.get("/health/services", response_model=ServiceHealth, tags=["system"])
def health_services(db: Session = Depends(get_db)):
    """Sistem statusu paneli üçün — hər sahə real yoxlamadan gəlir, heç nə fərz edilmir."""
    try:
        db.execute(text("SELECT 1"))
        postgres_ok = True
    except Exception:
        postgres_ok = False

    try:
        pgvector_ok = bool(
            db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).first()
        )
    except Exception:
        pgvector_ok = False

    last_run = crud.recent_ingest_runs(db, 1) if postgres_ok else []
    return ServiceHealth(
        postgres=postgres_ok,
        pgvector=pgvector_ok,
        redis=cache.ping(),
        groq_configured=bool(settings.groq_api_key),
        last_ingest_at=last_run[0].run_at if last_run else None,
        last_ingest_status=last_run[0].status if last_run else None,
    )


for r in (
    accounts.router,
    billing.router,
    library.router,
    ingest.router,
    papers.router,
    search.router,
    ask.router,
    analytics.router,
    logs.router,
    digests.router,
    intelligence.router,
):
    app.include_router(r)

class FrontendFiles(StaticFiles):
    """HTML həmişə yenidən yoxlanılsın; versiyalı asset-lər (?v=) keşdə qala bilər.

    Bunsuz brauzer köhnə index.html-i saxlayır və yeni CSS/JS heç yüklənmir.
    """

    def file_response(self, full_path, *args, **kwargs):
        response = super().file_response(full_path, *args, **kwargs)
        if str(full_path).endswith(".html"):
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


# Frontend ən sonda mount olunur ki, /api yollarını örtməsin
app.mount(
    "/",
    FrontendFiles(directory=Path(__file__).resolve().parent / "static", html=True),
    name="static",
)
