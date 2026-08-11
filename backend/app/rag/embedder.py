from functools import lru_cache

from fastembed import TextEmbedding

from ..config import settings


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    # İlk çağırışda model (~90 MB) yüklənir və /models volume-unda saxlanılır,
    # sonrakı restartlarda yenidən yüklənmir.
    return TextEmbedding(model_name=settings.embedding_model, cache_dir=settings.hf_cache_dir)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return [vec.tolist() for vec in _model().embed(texts)]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
