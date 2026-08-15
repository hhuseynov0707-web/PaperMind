"""Provider protokolları — §18.

Tələb: *«LLM, embedding and reranking providers should be replaceable without
rewriting business logic»*.

Dizayn qərarı — `Protocol`, abstrakt baza sinfi yox. Səbəb: provider-lər
xarici kitabxanaları örtür (groq, fastembed) və miras tələb etsək hər yeni
provider bizim sinifdən törəməli olardı. Protocol strukturaldır: uyğun metodu
olan istənilən obyekt işləyir, ona görə test üçün sadə saxta sinif yazmaq
kifayətdir — mock kitabxanası da lazım deyil.

Fabriklər `get_llm()` / `get_embedder()` şəklindədir və nəticəni keşləyir:
model yüklənməsi bahalıdır (fastembed ~90 MB), hər çağırışda yenidən qurulmamalıdır.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Mətn tamamlama. Biznes məntiqi yalnız bunu bilir."""

    name: str

    def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.3,
        max_tokens: int = 800,
        json_mode: bool = False,
        model: str | None = None,
    ) -> str:
        """Cavab mətnini qaytarır. Xəta halında istisna atır."""
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Mətn → vektor."""

    name: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


@runtime_checkable
class RerankProvider(Protocol):
    """Namizədləri sorğuya görə yenidən sıralayır.

    Hələ implementasiyası yoxdur — §5: rerank yalnız benchmark fayda göstərəndən
    sonra əlavə olunur. Protokol indidən var ki, o vaxt retriever-in imzası
    dəyişməsin.
    """

    name: str

    def rerank(self, query: str, documents: list[str], top_k: int) -> list[tuple[int, float]]:
        """[(orijinal_indeks, xal)] — azalan sıra ilə."""
        ...
