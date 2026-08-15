"""Cross-encoder rerank provider — §5.

Rerank NƏ ÜÇÜNDÜR: vektor axtarışı sorğunu və sənədi ayrı-ayrı kodlayır, ona
görə onların qarşılıqlı əlaqəsini görmür. Cross-encoder ikisini BİRLİKDƏ oxuyur
və dəqiqliyi adətən qaldırır — amma hər namizəd üçün model çağırışı tələb edir,
yəni bahadır.

Ona görə §5 şərt qoyur: *«Add reranking only if benchmarking demonstrates
meaningful improvement»*. Bu modul ölçmə üçün lazımdır; produksiyada isə
`RERANK_PROVIDER` boş qalır və heç nə dəyişmir.

Model seçimi: `BAAI/bge-reranker-base` ÇOXDİLLİDİR. Standart alternativ
(`ms-marco-MiniLM`) yalnız ingiliscədir və korpusumuzun rusdilli hissəsində
mənasız işləyərdi — eyni səhvi bir dəfə embedding modelində etmişdik.
"""

from ..config import settings


class FastEmbedRerank:
    name = "fastembed-rerank"

    def __init__(self, model_name: str | None = None, cache_dir: str | None = None):
        self._model_name = model_name or settings.rerank_model
        self._cache_dir = cache_dir or settings.hf_cache_dir
        self._model = None

    def _ensure(self):
        # Tənbəl yükləmə: model ~300 MB-dır və rerank sönülü olanda heç vaxt
        # lazım olmur. Xəta yalnız FAKTİKİ çağırışda atılır ki, provider-i
        # qeydiyyatdan keçirmək app-ı çökdürməsin.
        if self._model is None:
            try:
                from fastembed.rerank.cross_encoder import TextCrossEncoder
            except ImportError as exc:
                raise RuntimeError(
                    "Rerank üçün fastembed-in cross-encoder dəstəyi lazımdır "
                    "(fastembed>=0.4). requirements.txt yenilənməlidir."
                ) from exc
            self._model = TextCrossEncoder(
                model_name=self._model_name, cache_dir=self._cache_dir
            )
        return self._model

    def rerank(self, query: str, documents: list[str], top_k: int) -> list[tuple[int, float]]:
        """[(orijinal_indeks, xal)] — azalan sıra ilə, ilk `top_k`."""
        if not documents:
            return []
        scores = list(self._ensure().rerank(query, documents))
        ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)
        return [(i, float(s)) for i, s in ranked[:top_k]]
