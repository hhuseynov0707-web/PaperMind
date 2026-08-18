"""Şəxsi PDF qatı — parsing və giriş nəzarəti.

Bu qatda səhvin qiyməti xüsusidir: sənədlər İSTİFADƏÇİNİNDİR və şəxsidir.
Sızma bir sətir unudulmuş `user_id` filtri qədər yaxındır. Ona görə testlər
«işləyirmi» yox, «başqasının sənədinə çatmaq mümkündürmü» sualını verir.
"""

import io
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import pdf
from app.database import get_db
from app.main import app


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = lambda: MagicMock()
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _blank_pdf(pages: int = 1) -> bytes:
    """Mətnsiz, etibarlı PDF — skan edilmiş sənədi təqlid edir."""
    from pypdf import PdfWriter

    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


# --- Fayl tanınması ----------------------------------------------------------

def test_non_pdf_rejected_by_signature():
    """Uzantıya və Content-Type-a güvənmirik — ikisi də saxtalaşdırıla bilər."""
    assert not pdf.looks_like_pdf(b"GIF89a...")
    assert not pdf.looks_like_pdf(b"")
    assert pdf.looks_like_pdf(b"%PDF-1.7\n...")

    with pytest.raises(pdf.PdfError, match="PDF deyil"):
        pdf.extract_pages(b"this is plain text, not a pdf")


def test_oversized_file_rejected_before_parsing():
    """Limit parsing-dən ƏVVƏL yoxlanılır — 100 MB-lıq faylı açmaq
    yaddaşı partladar."""
    big = b"%PDF-" + b"x" * (pdf.MAX_BYTES + 1)
    with pytest.raises(pdf.PdfError, match="böyükdür"):
        pdf.extract_pages(big)


def test_scanned_pdf_gives_clear_reason():
    """Mətnsiz PDF SƏSSİZCƏ boş sənəd yaratmamalıdır.

    Əks halda istifadəçi «yükləndi» görür, sonra heç bir sual cavab almır və
    səbəbi bilmir — ən pis nəticə budur.
    """
    with pytest.raises(pdf.PdfError, match="skan"):
        pdf.parse(_blank_pdf(), "skan.pdf")


# --- Mətn təmizliyi və parçalama ---------------------------------------------

def test_line_break_hyphen_is_rejoined():
    """PDF sətir sonunda sözü defislə bölür. Birləşdirilməsə embedding
    «neu» və «ral» görür və axtarış zəifləyir."""
    assert "neural" in pdf._clean("neu-\nral networks")
    assert "soft" in pdf._clean("soft­hyphen").replace("hyphen", "")


def test_chunks_carry_their_page_number():
    """İstinadın dəqiqliyi buradan gəlir: hər parça BİR səhifəyə aiddir."""
    pages = ["birinci səhifə " * 30, "ikinci səhifə " * 30]
    chunks = pdf.chunk_pages(pages)
    assert chunks, "parça yaranmadı"
    assert {p for p, _ in chunks} <= {1, 2}
    assert all("birinci" in t for p, t in chunks if p == 1)
    assert all("ikinci" in t for p, t in chunks if p == 2)


def test_empty_pages_do_not_shift_numbering():
    """Boş səhifə buraxılır, amma NÖMRƏ sürüşmür — əks halda istinad
    yanlış səhifəni göstərər."""
    chunks = pdf.chunk_pages(["", "", "üçüncü səhifədəki mətn " * 20])
    assert chunks and all(p == 3 for p, _ in chunks)


def test_tiny_fragments_are_dropped():
    """Səhifə nömrəsi kimi qırıntılar indeksi zibilləyir."""
    assert pdf.chunk_pages(["12"]) == []


# --- Giriş nəzarəti ----------------------------------------------------------

def test_upload_requires_login(client):
    files = {"file": ("a.pdf", b"%PDF-1.7", "application/pdf")}
    assert client.post("/api/documents", files=files).status_code == 401


def test_list_requires_login(client):
    assert client.get("/api/documents").status_code == 401


def test_document_ask_requires_login(client):
    r = client.post("/api/documents/1/ask", json={"question": "nədir?"})
    assert r.status_code == 401


def test_free_user_cannot_upload(client):
    """PDF Pro imkanıdır — pulsuz istifadəçi 402 almalıdır, 401 yox.

    Fərq vacibdir: 401 «giriş et», 402 «planı yüksəlt» deməkdir və interfeys
    ikisini fərqli göstərir.
    """
    from app import models, plans
    from app.auth import require_user

    app.dependency_overrides[require_user] = lambda: models.User(
        id=1, email="free@example.com", password_hash="x", plan=plans.FREE
    )
    try:
        files = {"file": ("a.pdf", b"%PDF-1.7", "application/pdf")}
        r = client.post("/api/documents", files=files)
        assert r.status_code == 402
        assert r.json()["detail"]["error"] == "upgrade_required"
    finally:
        app.dependency_overrides.pop(require_user, None)


def test_owned_query_filters_by_user():
    """`_owned` sorğusunda İSTİFADƏÇİ filtri olmalıdır.

    Bu, sızmanın qarşısını alan yeganə sətirdir. Testi sorğunun mətni
    üzərində aparırıq, çünki DB olmadan davranışı yoxlamaq mümkün deyil —
    amma filtrin yoxa çıxmasını tutmaq üçün bu kifayətdir.
    """
    import inspect

    from app.routers import documents

    src = inspect.getsource(documents._owned)
    assert "user_id == user.id" in src, "istifadəçi filtri yoxdur — sızma riski"
