"""Sübut seçimi və istinad doğrulaması — Phase 3 (§8).

Auditdə tapılan boşluq: LLM istinad uydura bilirdi və bunu heç nə yoxlamırdı.
Prompt qaydası niyyət bildirir, zəmanət vermir.
"""

from types import SimpleNamespace

from app.rag.evidence import (
    MIN_EVIDENCE_SCORE,
    citation_label,
    corpus_context,
    select_evidence,
    validate_citations,
)


def _b(score):
    return {"score": score, "paper": None, "chunk": None}


# --------------------------------------------------------------------------
# İstinad etiketi — kontekst və doğrulama EYNİ olmalıdır
# --------------------------------------------------------------------------

def test_label_prefers_arxiv_then_doi_then_id():
    assert citation_label(SimpleNamespace(arxiv_id="2601.1", doi="10.1/a", id=5)) == "2601.1"
    assert citation_label(SimpleNamespace(arxiv_id=None, doi="10.1/a", id=5)) == "10.1/a"
    assert citation_label(SimpleNamespace(arxiv_id=None, doi=None, id=5)) == "id:5"


def test_label_never_none():
    """REGRESSION: `[None]` kontekstə düşəndə LLM onu bir neçə fərqli işə yapışdırırdı."""
    label = citation_label(SimpleNamespace(arxiv_id=None, doi=None, id=42))
    assert "None" not in label


# --------------------------------------------------------------------------
# Sübut seçimi
# --------------------------------------------------------------------------

def test_weak_results_dropped():
    """Zəif nəticə LLM-i çaşdırır: model kontekstdəki hər şeyi uyğun sayır."""
    kept, stats = select_evidence([_b(0.82), _b(0.78), _b(0.12), _b(0.05)])
    assert stats["kept"] == 2
    assert stats["dropped"] == 2


def test_relative_floor_drops_far_behind_results():
    """Mütləq həddi keçsə də liderdən çox uzaq düşən nəticə səs-küydür."""
    kept, _ = select_evidence([_b(0.90), _b(0.30)])
    assert len(kept) == 1


def test_at_least_one_block_survives():
    """Hamısı zəifdirsə susmaq yox, "zəif sübut var" demək daha faydalıdır."""
    kept, stats = select_evidence([_b(0.10), _b(0.08)])
    assert len(kept) == 1
    assert stats["weak"] is True


def test_strong_results_all_kept():
    kept, stats = select_evidence([_b(0.80), _b(0.78), _b(0.75)])
    assert stats["kept"] == 3
    assert stats["weak"] is False


def test_max_blocks_respected():
    kept, _ = select_evidence([_b(0.9) for _ in range(20)], max_blocks=5)
    assert len(kept) == 5


def test_empty_input():
    kept, stats = select_evidence([])
    assert kept == []
    assert stats["weak"] is True


def test_results_sorted_by_score():
    kept, _ = select_evidence([_b(0.60), _b(0.90), _b(0.75)])
    assert [b["score"] for b in kept] == [0.90, 0.75, 0.60]


def test_threshold_constant_is_sane():
    assert 0.0 < MIN_EVIDENCE_SCORE < 1.0


# --------------------------------------------------------------------------
# İstinad doğrulaması — §8 "Never fabricate citations"
# --------------------------------------------------------------------------

def test_invented_citation_removed():
    answer, stats = validate_citations(
        "Birinci iddia [10.1/a]. İkinci iddia [10.9/uydurma].", {"10.1/a"}
    )
    assert "10.9/uydurma" not in answer
    assert "[10.1/a]" in answer
    assert stats["invented"] == ["10.9/uydurma"]


def test_surrounding_text_survives_removal():
    """Yalnız istinad silinir — iddianın özü qalmalıdır."""
    answer, _ = validate_citations("Transformer arxitekturası effektivdir [saxta].", set())
    assert "Transformer arxitekturası effektivdir" in answer


def test_valid_citations_untouched():
    original = "İddia [2601.1] və digəri [10.1/b]."
    answer, stats = validate_citations(original, {"2601.1", "10.1/b"})
    assert answer == original
    assert stats["invented"] == []
    assert stats["valid"] == 2


def test_coverage_measures_evidence_use():
    """§20 citation completeness: verilən sübutun neçəsinə istinad edilib."""
    _, stats = validate_citations("Yalnız biri [a].", {"a", "b", "c", "d"})
    assert stats["coverage"] == 0.25


def test_no_citations_at_all():
    answer, stats = validate_citations("Heç bir istinad yoxdur.", {"a"})
    assert stats["cited"] == 0
    assert stats["coverage"] == 0.0


def test_repeated_invented_citation_removed_everywhere():
    answer, stats = validate_citations("[x] bir, [x] iki, [y] üç.", {"y"})
    assert "[x]" not in answer
    assert "[y]" in answer
    assert stats["invented"] == ["x"]


def test_spacing_cleaned_after_removal():
    answer, _ = validate_citations("İddia [saxta] .", set())
    assert "  " not in answer
    assert not answer.endswith(" .")


# --------------------------------------------------------------------------
# Korpus şəffaflığı (§16)
# --------------------------------------------------------------------------

def test_corpus_context_reports_scope():
    """Sistem heç vaxt bütün elmi ədəbiyyatı təmsil etdiyini ima etməməlidir."""
    ctx = corpus_context(1596, ["arxiv", "crossref"], ["en", "ru"])
    assert ctx["papers"] == 1596
    assert ctx["sources"] == ["arxiv", "crossref"]
    assert ctx["languages"] == ["en", "ru"]
