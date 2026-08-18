"""PDF emalı — §7 (şəxsi sənədlər).

Bu qat istifadəçinin YÜKLƏDİYİ faylı qəbul edir, yəni giriş düşmən ola bilər:
korlanmış fayl, parolla qorunan sənəd, 500 səhifəlik kitab, PDF adı verilmiş
şəkil. Testlər «düzgün fayl işləyirmi» yox, «SƏHV fayl nə edir» sualına
cavab verir — çünki ikincisi sistemi dayandırır.
"""

import io

import pytest
from pypdf import PdfWriter

from app import pdf


def _blank_pdf(pages: int = 1) -> bytes:
    """Mətnsiz, etibarlı PDF — skan edilmiş sənədi təqlid edir."""
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


# --- Fayl tanınması ---------------------------------------------------------

def test_signature_not_extension():
    """Uzantıya və Content-Type-a GÜVƏNMİRİK — hər ikisi saxtalaşdırıla bilər."""
    assert pdf.looks_like_pdf(b"%PDF-1.7\n...")
    assert not pdf.looks_like_pdf(b"\x89PNG\r\n\x1a\n")       # PNG
    assert not pdf.looks_like_pdf(b"<html>")
    assert not pdf.looks_like_pdf(b"")


def test_non_pdf_rejected_with_readable_reason():
    with pytest.raises(pdf.PdfError, match="PDF deyil"):
        pdf.extract_pages(b"bu sadece metndir" * 50)


def test_oversized_rejected_before_parsing():
    """Limit PARSE-dan əvvəl yoxlanılır: 20 MB-lıq zibili pypdf-ə vermək
    yaddaşı və CPU-nu boş yerə yandırır."""
    with pytest.raises(pdf.PdfError, match="böyükdür"):
        pdf.extract_pages(b"%PDF-" + b"x" * (pdf.MAX_BYTES + 1))


def test_page_limit_enforced():
    data = _blank_pdf(pdf.MAX_PAGES + 1)
    with pytest.raises(pdf.PdfError, match="Səhifə sayı"):
        pdf.extract_pages(data)


# --- Skan edilmiş sənəd -----------------------------------------------------

def test_scanned_pdf_fails_loudly_not_silently():
    """Ən vacib test.

    Şəkil kimi skan edilmiş PDF-dən mətn çıxmır. Səssiz keçsəydi, sənəd
    «yükləndi» görünər, sonra hər sualda «heç nə tapılmadı» deyərdi —
    istifadəçi üçün ən pis nəticə. Ona görə AÇIQ xəta verilir.
    """
    with pytest.raises(pdf.PdfError, match="skan"):
        pdf.parse(_blank_pdf(3), "skan.pdf")


def test_empty_upload_is_not_a_crash():
    with pytest.raises(pdf.PdfError):
        pdf.parse(b"", "bos.pdf")


# --- Mətn təmizləmə ---------------------------------------------------------

def test_line_break_hyphen_is_rejoined():
    """PDF sətir sonunda sözü defislə bölür. Birləşdirilməsə embedding
    «neu» və «ral» görür və axtarış zəifləyir."""
    assert "neural" in pdf._clean("neu-\nral network")
    assert "transformer" in pdf._clean("trans-\n  former")


def test_soft_hyphen_removed():
    assert pdf._clean("soft­hyphen") == "softhyphen"


def test_whitespace_collapsed_but_lines_kept():
    """Sətir sonları QALIR — `guess_title` birinci sətri oxuyur."""
    out = pdf._clean("Başlıq   burada\nikinci    sətir")
    assert "Başlıq burada" in out
    assert "\n" in out


# --- Səhifə-agah parçalama --------------------------------------------------

def test_page_numbers_start_at_one_and_survive_empty_pages():
    """Boş səhifə sırada qalmalıdır, əks halda sonrakı istinadlar sürüşür."""
    pages = ["birinci səhifənin mətni " * 10, "", "üçüncü səhifənin mətni " * 10]
    chunks = pdf.chunk_pages(pages)
    nums = {p for p, _ in chunks}
    assert 1 in nums and 3 in nums
    assert 2 not in nums          # boş səhifə chunk vermir
    assert min(nums) == 1         # 0-dan başlamır


def test_chunks_never_span_pages():
    """Hər chunk BİR səhifəyə aiddir — istinadın dəqiq olması buna bağlıdır."""
    pages = ["a" * 5000, "b" * 5000]
    for page, text in pdf.chunk_pages(pages):
        marker = "a" if page == 1 else "b"
        assert set(text) == {marker}


def test_tiny_fragments_dropped():
    """Səhifə nömrəsi və kolontitul kimi qırıntılar indeksi zibilləyir."""
    assert pdf.chunk_pages(["12", "", "  ."]) == []


# --- Başlıq və barmaq izi ---------------------------------------------------

def test_title_falls_back_to_filename():
    assert pdf.guess_title([], "sened.pdf") == "sened.pdf"
    assert pdf.guess_title(["qisa"], "sened.pdf") == "sened.pdf"


def test_title_skips_identifier_lines():
    pages = ["arXiv:2401.12345v2\nAttention Is All You Need\nAshish Vaswani"]
    assert pdf.guess_title(pages, "f.pdf") == "Attention Is All You Need"


def test_digest_is_content_addressed():
    """Eyni fayl → eyni barmaq izi. Təkrar yükləmənin tutulması buna əsaslanır."""
    a, b = _blank_pdf(1), _blank_pdf(1)
    assert pdf.file_digest(a) == pdf.file_digest(a)
    assert len(pdf.file_digest(a)) == 64
    # Fərqli məzmun fərqli həsh verir
    assert pdf.file_digest(a + b"x") != pdf.file_digest(a)
