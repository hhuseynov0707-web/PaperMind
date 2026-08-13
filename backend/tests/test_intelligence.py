"""Phase 4 — research intelligence testləri (§7, §9, §10, §12, §13).

Hamısı saf məntiqi yoxlayır: LLM cavabının PARSE və VALİDASİYASI, trend
arifmetikası, boşluq ifadəsi. LLM-in özü ölçülmür (o, rag_eval-ın işidir) —
burada yoxlanan şey odur ki, model səhv və ya zərərli cavab qaytaranda sistem
nə edir.
"""

import json

from app.landscape import GAP_PHRASING, find_gaps
from app.rag.compare import parse_comparison, parse_conflict
from app.rag.insights import (
    EVIDENCE_TYPES,
    INSIGHT_FIELDS,
    evidence_summary,
    parse_insight_response,
    verify_quotes,
)
from app.trends import classify_trend, classify_series


# ==========================================================================
# §7 — çıxarış
# ==========================================================================

ABSTRACT = (
    "We propose a new attention mechanism for long documents. "
    "Experiments on the arXiv dataset show a 12% improvement in perplexity. "
    "Our approach reduces memory usage during training."
)


def test_parse_extracts_fields_with_evidence():
    raw = json.dumps({
        "problem": {"value": "Long documents overflow attention.",
                    "evidence": "stated", "quote": "a new attention mechanism for long documents"},
        "findings": {"value": "12% perplexity gain.", "evidence": "stated",
                     "quote": "a 12% improvement in perplexity"},
        "methods": ["attention", "transformer"],
    })
    out = parse_insight_response(raw, ABSTRACT)
    assert out["problem"]["evidence"] == "stated"
    assert out["findings"]["quote"] == "a 12% improvement in perplexity"
    assert out["methods"] == ["attention", "transformer"]


def test_absent_fields_are_omitted_not_invented():
    """§7: «Never invent information that is absent from the paper.»

    Abstraktda məhdudiyyət yoxdursa, `null` DOĞRU cavabdır — boşluğu doldurmaq yox.
    """
    raw = json.dumps({"limitations": None, "future_work": {"value": "", "evidence": "stated"}})
    out = parse_insight_response(raw, ABSTRACT)
    assert "limitations" not in out
    assert "future_work" not in out


def test_unknown_evidence_type_degrades_to_inferred():
    """Naməlum etiket ən EHTİYATLI dəyərə çevrilməlidir.

    Modelin yoxlanıla bilməyən «stated» iddiasını fakt kimi göstərmək,
    sintezi nəticə kimi göstərməkdən qat-qat pisdir.
    """
    raw = json.dumps({"problem": {"value": "X", "evidence": "definitely-true"}})
    out = parse_insight_response(raw, ABSTRACT)
    assert out["problem"]["evidence"] == "inferred"


def test_fabricated_quote_is_removed_and_downgraded():
    """Model «stated» deyib abstraktda olmayan sitat gətirə bilər.

    Dəyərin doğruluğunu maşınla yoxlaya bilmirik, amma sitatın MÖVCUDLUĞUNU
    yoxlaya bilirik — §7-nin yeganə avtomatik yoxlanan hissəsi budur.
    """
    raw = json.dumps({
        "findings": {"value": "Huge gains.", "evidence": "stated",
                     "quote": "we achieved state of the art on every benchmark"},
    })
    out = parse_insight_response(raw, ABSTRACT)
    assert out["findings"]["quote"] is None
    assert out["findings"]["evidence"] == "synthesized"


def test_real_quote_survives_whitespace_differences():
    data = {"problem": {"value": "X", "evidence": "stated",
                        "quote": "a  new   attention\nmechanism"}}
    out = verify_quotes(data, ABSTRACT)
    assert out["problem"]["quote"] is not None
    assert out["problem"]["evidence"] == "stated"


def test_broken_json_returns_empty_not_crash():
    """Batch çıxarışda bir pis cavab bütün prosesi dayandırmamalıdır."""
    assert parse_insight_response("not json at all", ABSTRACT) == {}
    assert parse_insight_response("", ABSTRACT) == {}
    assert parse_insight_response('["list", "not", "object"]', ABSTRACT) == {}


def test_markdown_fenced_json_is_parsed():
    raw = '```json\n{"problem": {"value": "X", "evidence": "inferred"}}\n```'
    assert parse_insight_response(raw, ABSTRACT)["problem"]["value"] == "X"


def test_evidence_summary_counts_types():
    data = {
        "problem": {"value": "a", "evidence": "stated", "quote": "q"},
        "findings": {"value": "b", "evidence": "inferred", "quote": None},
    }
    s = evidence_summary(data)
    assert s["stated"] == 1 and s["inferred"] == 1
    assert s["fields_extracted"] == 2
    assert s["fields_possible"] == len(INSIGHT_FIELDS)
    assert s["quoted"] == 1


def test_evidence_types_are_the_three_required():
    assert set(EVIDENCE_TYPES) == {"stated", "synthesized", "inferred"}


# ==========================================================================
# §9 — müqayisə
# ==========================================================================

def test_comparison_marks_uncomparable_axes():
    raw = json.dumps({
        "axes": {"dataset": {"agreement": "not_comparable",
                             "summary": "Neither abstract names a dataset.",
                             "per_paper": {"1": "-", "2": "-"}}},
        "not_comparable": ["dataset"],
    })
    out = parse_comparison(raw)
    assert out["axes"]["dataset"]["agreement"] == "not_comparable"
    assert "dataset" in out["not_comparable"]


def test_comparison_unknown_agreement_becomes_not_comparable():
    raw = json.dumps({"axes": {"results": {"agreement": "sort-of", "summary": "x"}}})
    assert parse_comparison(raw)["axes"]["results"]["agreement"] == "not_comparable"


def test_comparison_broken_json_is_empty():
    out = parse_comparison("garbage")
    assert out["axes"] == {} and out["differences"] == []


# ==========================================================================
# §10 — ziddiyyət
# ==========================================================================

def test_differing_conditions_downgrade_direct_conflict():
    """§10-un mərkəzi qaydası: şərtlər fərqlidirsə, bu, tərifə görə birbaşa
    ziddiyyət DEYİL. Qayda kodda tətbiq olunur, prompt-a ümid edilmir."""
    raw = json.dumps({
        "classification": "direct_conflict",
        "reasoning": "Opposite results.",
        "differing_conditions": ["different patient population"],
        "confidence": "high",
    })
    assert parse_conflict(raw)["classification"] == "conditional_conflict"


def test_direct_conflict_survives_when_conditions_match():
    raw = json.dumps({
        "classification": "direct_conflict",
        "reasoning": "Same setup, opposite outcome.",
        "differing_conditions": [],
        "confidence": "high",
    })
    assert parse_conflict(raw)["classification"] == "direct_conflict"


def test_unknown_classification_defaults_to_no_conflict():
    """Səhvən «ziddiyyət var» demək istifadəçini yanlış yönləndirir;
    ziddiyyəti gözdən qaçırmaq isə yalnız məlumat itkisidir."""
    raw = json.dumps({"classification": "totally_opposite", "confidence": "high"})
    out = parse_conflict(raw)
    assert out["classification"] == "no_conflict"


def test_conflict_never_declares_a_winner():
    """Cavab strukturunda «hansı doğrudur» sahəsi ola bilməz (§10)."""
    raw = json.dumps({
        "classification": "direct_conflict", "correct_paper": "1",
        "winner": "1", "differing_conditions": [], "confidence": "high",
    })
    out = parse_conflict(raw)
    assert "correct_paper" not in out and "winner" not in out


def test_conflict_broken_json_is_conservative():
    out = parse_conflict("}{")
    assert out["classification"] == "no_conflict"
    assert out["confidence"] == "low"


# ==========================================================================
# §12 — trend təsnifatı
# ==========================================================================

def test_insufficient_data_when_series_too_short():
    out = classify_trend([5, 6, 7], "ai")
    assert out["classification"] == "INSUFFICIENT_DATA"
    assert "həftə" in out["reason"]


def test_insufficient_data_when_counts_too_small():
    """1 → 2 məqalə +100%-dir, amma trend deyil, təsadüfdür."""
    out = classify_trend([0, 1, 0, 1, 0, 2, 1, 0], "rare")
    assert out["classification"] == "INSUFFICIENT_DATA"


def test_growing_series():
    out = classify_trend([3, 3, 4, 4, 8, 9, 10, 11], "ai")
    assert out["classification"] == "GROWING"
    assert "%" in out["reason"]


def test_declining_series():
    out = classify_trend([12, 11, 10, 9, 4, 3, 3, 2], "old")
    assert out["classification"] == "DECLINING"


def test_stable_series():
    out = classify_trend([6, 7, 6, 7, 6, 7, 7, 6], "steady")
    assert out["classification"] == "STABLE"
    assert "səs-küy" in out["reason"]


def test_emerging_series():
    """Sıfıra yaxın bazadan qalxma — faiz hesablana bilmir, ayrıca sinif lazımdır."""
    out = classify_trend([0, 0, 1, 0, 5, 6, 7, 8], "new-topic")
    assert out["classification"] == "EMERGING"


def test_every_classification_explains_itself():
    """§12: «Explain why a topic received its classification.»"""
    for counts in ([3, 3, 4, 4, 8, 9, 10, 11], [12, 11, 10, 9, 4, 3, 3, 2],
                   [6, 7, 6, 7, 6, 7, 7, 6], [0, 0, 1, 0, 5, 6, 7, 8], [1, 2]):
        out = classify_trend(counts, "x")
        assert out["reason"] and len(out["reason"]) > 20


def test_series_sorted_by_actionability():
    series = {
        "stable": [6, 7, 6, 7, 6, 7, 7, 6],
        "emerging": [0, 0, 1, 0, 5, 6, 7, 8],
        "growing": [3, 3, 4, 4, 8, 9, 10, 11],
    }
    order = [r["label"] for r in classify_series(series)]
    assert order[0] == "emerging"
    assert order.index("growing") < order.index("stable")


# ==========================================================================
# §13 — boşluqlar
# ==========================================================================

class _P:
    def __init__(self, pid, title, fields, lang="en"):
        self.id, self.title, self.field_keys, self.language = pid, title, fields, lang
        self.doi = self.arxiv_id = self.published_at = None
        self.authors = []


def test_gap_output_is_labelled_as_ai_generated():
    """§13: nəticə açıq şəkildə AI nəticəsi kimi etiketlənməlidir."""
    out = find_gaps([_P(1, "A", ["ai"])], {}, "az")
    assert out["label"] == "AI-GENERATED RESEARCH OPPORTUNITIES"


def test_gap_phrasing_never_claims_absence():
    """§13: «There is no research on X» QADAĞANDIR.

    İcazə verilən ifadə yalnız indeksin məhdudiyyətini bildirir.
    """
    for lang, template in GAP_PHRASING.items():
        low = template.lower()
        assert "no research" not in low
        assert "tədqiqat yoxdur" not in low
        assert "нет исследований" not in low
        assert "{topic}" in template and "{n}" in template


def test_gaps_expose_their_evidence_base():
    """Çıxarışı olmayan məqalə siqnal verə bilməz — bu, gizlədilməməlidir."""
    papers = [_P(1, "A", ["ai"]), _P(2, "B", ["ai"])]
    insights = {1: {"limitations": {"value": "small sample", "evidence": "stated"}}}
    out = find_gaps(papers, insights, "az")
    assert out["evidence_base"]["papers_examined"] == 2
    assert out["evidence_base"]["papers_with_insights"] == 1
    assert out["evidence_base"]["coverage"] == 0.5


def test_gap_signals_carry_evidence_type():
    """«inferred» məhdudiyyət məqalənin yazdığı deyil, modelin nəticəsidir."""
    papers = [_P(1, "A", ["ai"])]
    insights = {1: {"limitations": {"value": "maybe biased", "evidence": "inferred"}}}
    out = find_gaps(papers, insights, "az")
    assert out["repeated_limitations"][0]["evidence"] == "inferred"


# ==========================================================================
# §12 — indeks əhatəsi (real ölçmədə tapılan səhv)
# ==========================================================================

def test_index_coverage_blocks_false_emerging():
    """REGRESSION: canlı sistemdə «təbiət elmləri YENİ YARANIR — əvvəlki yarıda
    0, son yarıda 276 məqalə» çıxdı.

    Arifmetika düzgün idi, nəticə isə yanlış: həmin sahəni biz yenicə yığmağa
    başlamışdıq. Bu, ədəbiyyatın deyil, indeksləmə tarixçəmizin artefaktıdır.
    """
    out = classify_trend([0, 0, 0, 0, 90, 95, 91], "natural",
                         coverage=[0, 0, 0, 0, 300, 320, 310])
    assert out["classification"] == "INSUFFICIENT_DATA"
    assert "əhatəsi" in out["reason"]


def test_real_emerging_survives_when_index_covers_period():
    """Əhatə hər iki yarıda varsa, EMERGING həqiqi siqnaldır və qalmalıdır."""
    out = classify_trend([0, 1, 0, 0, 8, 9, 10], "new-topic",
                         coverage=[100, 110, 105, 108, 115, 120, 118])
    assert out["classification"] == "EMERGING"


def test_real_growth_survives():
    out = classify_trend([10, 11, 12, 13, 20, 22, 24], "ai",
                         coverage=[100, 110, 105, 108, 115, 120, 118])
    assert out["classification"] == "GROWING"


def test_series_derives_coverage_from_topics():
    """Əhatə verilməyəndə mövzuların cəmindən hesablanır — endpoint bunu
    ayrıca ötürməyi unutsa da qoruma işləməlidir."""
    series = {
        "natural": [0, 0, 0, 0, 90, 95, 91],
        "tech": [0, 0, 0, 0, 40, 45, 44],
    }
    for row in classify_series(series):
        assert row["classification"] == "INSUFFICIENT_DATA"
