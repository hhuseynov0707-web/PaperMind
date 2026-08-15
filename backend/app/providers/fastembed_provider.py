"""fastembed embedding provider — §18.

Model yüklənməsi bahalıdır (~90 MB, `/models` volume-unda keşlənir), ona görə
instansiya bir dəfə qurulur və saxlanılır.
"""

from functools import lru_cache

from ..config import settings


class FastEmbedProvider:
    name = "fastembed"

    def __init__(self, model_name: str | None = None, cache_dir: str | None = None):
        self._model_name = model_name or settings.embedding_model
        self._cache_dir = cache_dir or settings.hf_cache_dir
        self.dim = settings.embedding_dim

    @lru_cache(maxsize=1)
    def _model(self):
        from fastembed import TextEmbedding
        return TextEmbedding(model_name=self._model_name, cache_dir=self._cache_dir)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return [vec.tolist() for vec in self._model().embed(texts)]
