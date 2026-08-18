"""PDF oxuma və səhifə-agah parçalama.

**Kitabxana seçimi — pypdf (BSD).** PyMuPDF daha sürətlidir və düzümü daha
yaxşı saxlayır, amma **AGPL** lisenziyalıdır: onu şəbəkə xidmətində işlətmək
bütün mənbə kodunu açmağa məcbur edir. Ödənişli məhsulda bu qəbuledilməzdir.
pdfplumber (MIT) da var, lakin pypdf üzərində qurulub və bizə lazım olmayan
cədvəl/düzüm analizi gətirir.

**Səhifə-agahlıq qəsdəndir.** Hər chunk BİR səhifəyə aiddir, səhifələr arası
kəsilmir. Beləliklə hər istinad dəqiq səhifə nömrəsi ilə göstərilə bilir —
«Paper → Page → Passage». Qiyməti: səhifə sərhədində kontekst qırılır. Bu,
şüurlu mübadilədir: yanlış səhifə göstərmək, bir az kontekst itirməkdən pisdir.
"""

import hashlib
import io
import re

from .config import settings
from .rag.chunker import chunk_text

# Limitlər həm sui-istifadəyə, həm də yaddaşa qarşıdır. Backend konteynerinin
# limiti 2 GB-dır və embedding eyni prosesdə işləyir.
MAX_BYTES = 20 * 1024 * 1024      # 20 MB
MAX_PAGES = 300
MIN_TEXT_CHARS = 200               # bundan azdırsa mətn çıxarıla bilməyib


class PdfError(Exception):
    """İstifadəçiyə göstərilə bilən səbəblə uğursuzluq."""


def file_digest(data: bytes) -> str:
    """Eyni faylın təkrar yüklənməsini tutmaq üçün."""
    return hashlib.sha256(data).hexdigest()


def looks_like_pdf(data: bytes) -> bool:
    """Uzantıya və ya `Content-Type`-a GÜVƏNMİRİK — hər ikisi saxtalaşdırıla
    bilər. Fayl imzası yoxlanılır."""
    return data[:5] == b"%PDF-"


def _clean(text: str) -> str:
    """Sətir sonu defislərini birləşdirir və artıq boşluqları yığır.

    PDF-də sətir sonunda sözlər defislə bölünür («neu-\nral»). Təmizlənməsə
    embedding «neu» və «ral» görür və axtarış zəifləyir.
    """
    text = text.replace("\u00ad", "")                    # soft hyphen
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)   # sətir sonu defisi
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def extract_pages(data: bytes) -> list[str]:
    """Səhifə-səhifə mətn. Boş səhifələr də sırada qalır ki, nömrələr sürüşməsin."""
    if len(data) > MAX_BYTES:
        raise PdfError(f"Fayl çox böyükdür ({len(data) // 1024 // 1024} MB). Limit: {MAX_BYTES // 1024 // 1024} MB.")
    if not looks_like_pdf(data):
        raise PdfError("Bu fayl PDF deyil.")

    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise PdfError(f"PDF oxunmadı: {str(exc)[:120]}") from exc

    if getattr(reader, "is_encrypted", False):
        # Bəzi PDF-lər boş parolla açılır; əvvəlcə onu sınayırıq.
        try:
            if reader.decrypt("") == 0:
                raise PdfError("PDF parolla qorunub.")
        except PdfError:
            raise
        except Exception as exc:
            raise PdfError("PDF parolla qorunub.") from exc

    total = len(reader.pages)
    if total == 0:
        raise PdfError("PDF boşdur.")
    if total > MAX_PAGES:
        raise PdfError(f"Səhifə sayı çoxdur ({total}). Limit: {MAX_PAGES}.")

    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(_clean(page.extract_text() or ""))
        except Exception:
            # Bir səhifənin sınması bütün sənədi itirməməlidir — boş qalır,
            # nömrələmə isə pozulmur.
            pages.append("")
    return pages


def chunk_pages(pages: list[str]) -> list[tuple[int, str]]:
    """(səhifə_nömrəsi, chunk) siyahısı. Səhifə nömrəsi 1-dən başlayır."""
    out: list[tuple[int, str]] = []
    for i, text in enumerate(pages, start=1):
        for chunk in chunk_text(text, settings.chunk_size, settings.chunk_overlap):
            if len(chunk.strip()) >= 40:      # cüzi qırıntılar indeksi zibilləyir
                out.append((i, chunk))
    return out


def guess_title(pages: list[str], fallback: str) -> str:
    """Birinci səhifənin ilk mənalı sətri başlıq kimi götürülür.

    Dəqiq deyil və olmasına ehtiyac yoxdur — istifadəçi sənədi öz faylının
    adı ilə tanıyır; bu, yalnız siyahını oxunaqlı edir.
    """
    if not pages:
        return fallback
    for line in pages[0].split("\n"):
        line = line.strip()
        if 15 <= len(line) <= 200 and not line.lower().startswith(("arxiv:", "doi:")):
            return line
    return fallback


def parse(data: bytes, filename: str) -> dict:
    """Yüklənmiş faylı emala hazır formaya çevirir.

    Mətn çıxarıla bilməyəndə AÇIQ xəta verilir. Səbəb: skan edilmiş PDF-lər
    boş mətn qaytarır və sənəd səssizcə «yükləndi, amma heç nə tapılmır»
    vəziyyətinə düşərdi — istifadəçi üçün ən pis nəticə.
    """
    pages = extract_pages(data)
    joined = "".join(pages)
    if len(joined) < MIN_TEXT_CHARS:
        raise PdfError(
            "Bu PDF-dən mətn çıxarıla bilmədi — çox güman skan edilmiş şəkildir. "
            "Mətn qatı olan PDF lazımdır."
        )
    chunks = chunk_pages(pages)
    if not chunks:
        raise PdfError("PDF-də indeksləşdiriləcək mətn tapılmadı.")
    return {
        "pages": len(pages),
        "chars": len(joined),
        "title": guess_title(pages, filename),
        "chunks": chunks,
        "digest": file_digest(data),
    }
