from ..config import settings


def chunk_text(text: str, size: int | None = None, overlap: int | None = None) -> list[str]:
    """Mətni ~size simvolluq, overlap qədər üst-üstə düşən parçalara bölür.

    Sərhədi söz ortasında yox, ən yaxın boşluqda kəsir. arXiv abstraktlarının
    çoxu 1 chunk-a sığır — uzunları isə burada bölünür.
    """
    size = size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap
    text = " ".join(text.split())
    if not text:
        return []
    if len(text) <= size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            space = text.rfind(" ", start, end)
            if space > start:
                end = space
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


def embedding_text(title: str | None, content: str) -> str:
    """Vektorlaşdırılacaq mətn: başlıq + chunk.

    Niyə ayrıca funksiya: SAXLANILAN `content` dəyişmir (LLM konteksti başlığı
    onsuz da ayrıca alır, təkrarlanmamalıdır), amma EMBED olunan mətnə başlıq
    əlavə olunur.

    Səbəb iki qatlıdır:
      1. Məhsul: istifadəçi məqaləni başlıqla axtaranda semantik axtarış onu
         tapmalıdır — abstraktda başlıq sözləri olmaya bilər.
      2. Ölçmə: leksik indeksdə (sv_en/sv_ru) başlıq var. Vektorda olmasa,
         iki üsulun müqayisəsi üsulu deyil, indeksin məzmununu ölçür.

    Bu funksiyanı həm ingest (crud.upsert_papers), həm də reembed işlədir ki,
    korpusda iki fərqli təmsil qarışmasın.
    """
    title = (title or "").strip()
    return f"{title}\n{content}" if title else content


# Vektorun TƏMSİL versiyası. Model adı ilə birlikdə saxlanılır, çünki vektoru
# köhnəldən yeganə şey model deyil — embed olunan mətnin quruluşu da ola bilər.
# "title-v1" = başlıq + chunk (əvvəllər yalnız chunk idi).
# Bu sətri dəyişəndə reembed.py bütün korpusu yenidən hesablayır.
EMBED_VARIANT = "title-v1"


def embedding_signature(model: str) -> str:
    """`chunks.embedding_model` sütununda saxlanılan dəyər."""
    return f"{model}#{EMBED_VARIANT}"
