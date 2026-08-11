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
