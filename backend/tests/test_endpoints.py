"""Endpoint testləri — auditin 1.5 maddəsi (§21).

Niyə lazımdır: `SourceOut.arxiv_id` məcburi olduğu üçün arXiv-dən kənar
məqaləyə istinad edən HƏR cavab `500` qaytarırdı (korpusun yarıdan çoxu belədir).
O vaxtkı testlərin heç biri bunu tutmadı, çünki heç biri HTTP cavabına baxmırdı.

Bu testlər DB və embedding modeli TƏLƏB ETMİR: `get_db` override olunur və
yalnız model/validasiya/təhlükəsizlik qatı yoxlanılır. Retrieval-in özü
`test_dedup.py` (real DB) və benchmark ilə ölçülür.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import get_db
from app.main import app


@pytest.fixture
def client():
    """Lifespan işə salınmır — o, miqrasiya üçün DB tələb edir.

    TestClient kontekst meneceri kimi İŞLƏDİLMİR, ona görə startup hadisələri
    keçilir; endpoint-lər isə normal cavab verir.
    """
    # Sessiya YERİNƏ mock qoyulur, xəta atılmır: FastAPI asılılıqları
    # validasiyadan əvvəl həll edir, ona görə burada raise etsək 422 gözlədiyimiz
    # yerdə 500 alarıq və test səhv şeyi ölçər.
    app.dependency_overrides[get_db] = lambda: MagicMock()
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture
def public_mode():
    """İctimai rejimi müvəqqəti açır (yazma endpoint-ləri açar tələb edir)."""
    old_mode, old_key = settings.public_mode, settings.admin_api_key
    settings.public_mode, settings.admin_api_key = True, "test-key-12345"
    yield
    settings.public_mode, settings.admin_api_key = old_mode, old_key


# --------------------------------------------------------------------------
# Validasiya — DB-yə çatmadan rədd edilməlidir
# --------------------------------------------------------------------------

def test_unknown_field_rejected_on_search(client):
    r = client.get("/api/search", params={"q": "machine learning", "field": "yoxdur"})
    assert r.status_code == 422


def test_unknown_field_rejected_on_papers(client):
    r = client.get("/api/papers", params={"field": "yoxdur"})
    assert r.status_code == 422


def test_unknown_field_rejected_on_ask(client):
    r = client.post("/api/ask", json={"question": "nədir bu?", "field": "yoxdur"})
    assert r.status_code == 422


def test_too_short_query_rejected(client):
    assert client.get("/api/search", params={"q": "a"}).status_code == 422


def test_too_long_query_rejected(client):
    assert client.get("/api/search", params={"q": "x" * 500}).status_code == 422


def test_page_size_bounded(client):
    assert client.get("/api/papers", params={"page_size": 1000}).status_code == 422


def test_days_bounded(client):
    assert client.get("/api/papers", params={"days": 9999}).status_code == 422


# --------------------------------------------------------------------------
# Təhlükəsizlik — yazma endpoint-ləri (§17)
# --------------------------------------------------------------------------

def test_ingest_requires_key_in_public_mode(client, public_mode):
    r = client.post("/api/ingest", json={"papers": []})
    assert r.status_code == 401


def test_ingest_pull_requires_key_in_public_mode(client, public_mode):
    r = client.post("/api/ingest/pull", json={"source": "arxiv", "days": 1})
    assert r.status_code == 401


def test_wrong_key_rejected(client, public_mode):
    r = client.post("/api/ingest", json={"papers": []}, headers={"X-API-Key": "wrong-key"})
    assert r.status_code == 401


def test_error_log_write_requires_key(client, public_mode):
    r = client.post("/api/logs/error", json={"workflow": "W1", "message": "test"})
    assert r.status_code in (401, 404, 422)


def test_reads_do_not_require_key(client, public_mode):
    """Oxu endpoint-ləri ictimai rejimdə də açıq qalmalıdır."""
    r = client.get("/api/search", params={"q": "x"})
    assert r.status_code != 401


# --------------------------------------------------------------------------
# Cavab modelləri — 500-ə səbəb olan regression
# --------------------------------------------------------------------------

def test_source_without_arxiv_id_serializes():
    """REGRESSION: korpusun yarıdan çoxu arXiv-dən kənardır.

    `arxiv_id` məcburi olanda belə mənbələrə istinad edən hər cavab 500 verirdi.
    """
    from app.schemas import AskResponse

    resp = AskResponse(
        answer="Cavab [10.1234/abc]",
        sources=[{
            "arxiv_id": None,
            "doi": "10.1234/abc",
            "title": "Crossref-dən gələn məqalə",
            "score": 0.91,
            "pdf_url": None,
        }],
        from_cache=False,
        latency_ms=42,
    )
    assert resp.sources[0].arxiv_id is None
    assert resp.sources[0].doi == "10.1234/abc"


def test_source_without_any_identifier_serializes():
    """Nə arXiv ID, nə DOI — yalnız başlıq. Cavab yenə də qurulmalıdır."""
    from app.schemas import AskResponse

    resp = AskResponse(
        answer="Cavab",
        sources=[{"arxiv_id": None, "doi": None, "title": "Başlıqsız mənbə",
                  "score": 0.5, "pdf_url": None}],
        from_cache=False,
        latency_ms=1,
    )
    assert resp.sources[0].title == "Başlıqsız mənbə"


# --------------------------------------------------------------------------
# Sağlamlıq
# --------------------------------------------------------------------------

def test_health_is_open(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_openapi_schema_builds(client):
    """Bütün Pydantic modelləri bir-birinə uyğun olmalıdır."""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert "/api/search" in r.json()["paths"]
