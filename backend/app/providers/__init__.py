"""Provider registry — §18.

Provider seçimi KONFİQURASİYADAN gəlir, koddan yox. Yeni provider əlavə etmək
üçün bir modul yazıb bu registry-yə bir sətir düşür; biznes məntiqinə
toxunulmur.

    LLM_PROVIDER=groq          # .env
    EMBEDDING_PROVIDER=fastembed
"""

from functools import lru_cache

from ..config import settings
from .base import EmbeddingProvider, LLMProvider, RerankProvider

_LLM_REGISTRY = {}
_EMBEDDING_REGISTRY = {}
_RERANK_REGISTRY = {}


def _register_defaults() -> None:
    """Tənbəl qeydiyyat: modul importu ağır kitabxana çəkməsin."""
    if _LLM_REGISTRY:
        return
    from .fastembed_provider import FastEmbedProvider
    from .groq_provider import GroqLLM
    from .rerank_provider import FastEmbedRerank
    _LLM_REGISTRY["groq"] = GroqLLM
    _EMBEDDING_REGISTRY["fastembed"] = FastEmbedProvider
    _RERANK_REGISTRY["fastembed"] = FastEmbedRerank


@lru_cache(maxsize=4)
def get_llm(name: str | None = None) -> LLMProvider:
    _register_defaults()
    key = name or settings.llm_provider
    if key not in _LLM_REGISTRY:
        raise ValueError(
            f"Naməlum LLM provider: {key}. Mövcud: {', '.join(sorted(_LLM_REGISTRY))}"
        )
    return _LLM_REGISTRY[key]()


@lru_cache(maxsize=4)
def get_embedder(name: str | None = None) -> EmbeddingProvider:
    _register_defaults()
    key = name or settings.embedding_provider
    if key not in _EMBEDDING_REGISTRY:
        raise ValueError(
            f"Naməlum embedding provider: {key}. Mövcud: {', '.join(sorted(_EMBEDDING_REGISTRY))}"
        )
    return _EMBEDDING_REGISTRY[key]()


@lru_cache(maxsize=4)
def get_reranker(name: str | None = None) -> RerankProvider | None:
    """Rerank provider — SÖNÜLÜ olanda None qaytarır.

    None qaytarmaq istisna atmaqdan yaxşıdır: çağıran tərəf «rerank varsa
    işlət» məntiqini bir `if` ilə yaza bilir və rerank sönülü mühitdə heç nə
    dəyişmir.
    """
    _register_defaults()
    key = name if name is not None else settings.rerank_provider
    if not key:
        return None
    if key not in _RERANK_REGISTRY:
        raise ValueError(
            f"Naməlum rerank provider: {key}. Mövcud: {', '.join(sorted(_RERANK_REGISTRY))}"
        )
    return _RERANK_REGISTRY[key]()


def register_llm(name: str, factory) -> None:
    """Test və genişlənmə üçün: provider-i çalışma zamanı əlavə edir."""
    _register_defaults()
    _LLM_REGISTRY[name] = factory
    get_llm.cache_clear()


def register_embedder(name: str, factory) -> None:
    _register_defaults()
    _EMBEDDING_REGISTRY[name] = factory
    get_embedder.cache_clear()


def register_reranker(name: str, factory) -> None:
    _register_defaults()
    _RERANK_REGISTRY[name] = factory
    get_reranker.cache_clear()


__all__ = [
    "EmbeddingProvider", "LLMProvider", "RerankProvider",
    "get_llm", "get_embedder", "get_reranker",
    "register_llm", "register_embedder", "register_reranker",
]
