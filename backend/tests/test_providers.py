"""Provider abstraksiyası — §18.

Tələb: *«LLM, embedding and reranking providers should be replaceable without
rewriting business logic»*. Bu testlər məhz onu yoxlayır — biznes məntiqi
provider dəyişəndə TOXUNULMADAN işləməlidir.
"""

import pytest

from app.providers import (
    get_embedder,
    get_llm,
    register_embedder,
    register_llm,
)
from app.providers.base import EmbeddingProvider, LLMProvider, RerankProvider


class FakeLLM:
    """Protocol strukturaldır — miras lazım deyil, uyğun metod kifayətdir."""

    name = "fake"

    def __init__(self):
        self.calls = []

    def complete(self, system, user, *, temperature=0.3, max_tokens=800,
                 json_mode=False, model=None):
        self.calls.append({"system": system, "user": user, "json": json_mode,
                           "model": model, "temperature": temperature})
        return '{"ok": true}' if json_mode else "saxta cavab"


class FakeEmbedder:
    name = "fake-emb"
    dim = 3

    def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def test_default_providers_satisfy_protocols():
    assert isinstance(get_llm(), LLMProvider)
    assert isinstance(get_embedder(), EmbeddingProvider)


def test_fake_llm_satisfies_protocol_without_inheritance():
    """Protocol seçildi ki, provider bizim sinifdən törəməsin — test üçün
    sadə sinif kifayət etsin, mock kitabxanası lazım olmasın."""
    assert isinstance(FakeLLM(), LLMProvider)


def test_llm_is_swappable_by_name():
    register_llm("test-swap", FakeLLM)
    assert get_llm("test-swap").complete("s", "u") == "saxta cavab"


def test_embedder_is_swappable_by_name():
    register_embedder("test-emb", FakeEmbedder)
    vecs = get_embedder("test-emb").embed(["a", "b"])
    assert len(vecs) == 2 and len(vecs[0]) == 3


def test_business_logic_uses_injected_provider(monkeypatch):
    """Əsas yoxlama: `ask_llm` Groq-a deyil, PROVIDER-ə müraciət edir.

    Bu keçirsə, provider dəyişdirmək üçün biznes məntiqinə toxunmaq lazım deyil.
    """
    from app.rag import llm as llm_mod

    fake = FakeLLM()
    monkeypatch.setattr(llm_mod, "get_llm", lambda *a, **k: fake)
    monkeypatch.setattr(llm_mod.settings, "groq_api_key", "test")

    class P:
        title = "Test paper"

    class C:
        content = "Test content"

    out = llm_mod.ask_llm("sual?", [{"paper": P(), "chunk": C()}], lang="az")
    assert out == "saxta cavab"
    assert len(fake.calls) == 1

    # Audit S1: sənəd MƏZMUNU user mesajında olmalıdır, system-də yox.
    # Diqqət: system prompt `<evidence>` sözünü təlimat kimi çəkir və bu,
    # düzgündür — yoxlanan şey taqın adı deyil, MƏTNİN özüdür.
    assert "Test content" in fake.calls[0]["user"]
    assert "Test paper" in fake.calls[0]["user"]
    assert "Test content" not in fake.calls[0]["system"]
    assert "Test paper" not in fake.calls[0]["system"]


def test_extraction_uses_small_model_and_json_mode(monkeypatch):
    """Çıxarış ayrı modeldən və JSON rejimindən istifadə etməlidir —
    70B ilə rate limit-ə dirənmişdik."""
    from app.rag import insights as ins_mod
    from app import providers as prov

    fake = FakeLLM()
    monkeypatch.setattr(prov, "get_llm", lambda *a, **k: fake)
    ins_mod.extract_insight("Başlıq", "Abstrakt mətni")

    assert fake.calls[0]["json"] is True
    assert fake.calls[0]["model"] == ins_mod.settings.extract_model
    assert fake.calls[0]["temperature"] == 0.0


def test_unknown_provider_fails_loudly():
    with pytest.raises(ValueError, match="Naməlum"):
        get_llm("bele-provider-yoxdur")


def test_rerank_protocol_exists_but_unimplemented():
    """§5: rerank yalnız ölçmə fayda göstərəndən sonra əlavə olunur.
    Protokol indidən var ki, o vaxt retriever imzası dəyişməsin."""
    assert hasattr(RerankProvider, "rerank")
