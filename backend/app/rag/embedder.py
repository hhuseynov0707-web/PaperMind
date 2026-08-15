"""Embedding — nazik örtük.

Faktiki implementasiya `app/providers/`-dədir (§18). Bu modul qalır, çünki
kod bazasında `embed_texts` onlarla yerdə çağırılır və provider abstraksiyası
üçün hamısını dəyişmək lazımsız risk idi.
"""

from ..providers import get_embedder


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return get_embedder().embed(texts)


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
