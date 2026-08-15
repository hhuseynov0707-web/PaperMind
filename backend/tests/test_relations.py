"""Məqalələr arası əlaqələr — §15 testləri.

Mərkəzi prinsip: əlaqələr etibarlılıq baxımından BƏRABƏR DEYİL. `cites` xarici
reyestrdən gələn faktdır, `related_to` isə ölçülmüş oxşarlıqdır. Bu fərq
itirilsə, sistem inandırıcı görünən uydurmaya çevrilir.
"""

from app.relations import (
    CONFIDENCE,
    RELATION_TYPES,
    author_overlap,
    build_relation,
    classify_citation_direction,
    method_overlap,
    normalize_openalex_refs,
    summarize_relations,
)


# --------------------------------------------------------------------------
# Əlaqə qurulması
# --------------------------------------------------------------------------

def test_self_relation_rejected():
    """Öz-özünə əlaqə qrafikdə mənasızdır və keçid sorğularında dövrə yaradır."""
    assert build_relation(5, 5, "cites", source="openalex") is None


def test_unknown_relation_type_rejected():
    assert build_relation(1, 2, "uydurma-tip", source="openalex") is None


def test_missing_id_rejected():
    assert build_relation(0, 2, "cites", source="openalex") is None
    assert build_relation(1, None, "cites", source="openalex") is None


def test_citation_is_a_fact_with_full_confidence():
    r = build_relation(1, 2, "cites", source="openalex")
    assert r["confidence"] == 1.0
    assert r["source"] == "openalex"


def test_similarity_link_is_weaker_than_citation():
    """Ölçülmüş oxşarlıq faktla eyni etibarda göstərilə bilməz."""
    cite = build_relation(1, 2, "cites", source="openalex")
    similar = build_relation(1, 3, "related_to", source="similarity")
    assert similar["confidence"] < cite["confidence"]


def test_explicit_confidence_overrides_default():
    r = build_relation(1, 2, "related_to", source="similarity", confidence=0.83)
    assert r["confidence"] == 0.83


def test_evidence_is_truncated_not_dropped():
    r = build_relation(1, 2, "cites", source="openalex", evidence="x" * 900)
    assert len(r["evidence"]) == 500


def test_all_relation_types_have_a_confidence_source():
    """Hər əlaqə mənbəyi tanınmalıdır, yoxsa etibarlılıq təsadüfi olur."""
    for source in CONFIDENCE:
        assert 0 < CONFIDENCE[source] <= 1.0


# --------------------------------------------------------------------------
# Sitat istiqaməti
# --------------------------------------------------------------------------

def test_later_paper_citing_earlier_is_builds_on():
    assert classify_citation_direction(2024, 2020) == "builds_on"


def test_unknown_dates_stay_as_plain_citation():
    """Naməlum halda daha ZƏİF iddia seçilir — `builds_on` əlavə məna daşıyır."""
    assert classify_citation_direction(None, 2020) == "cites"
    assert classify_citation_direction(2024, None) == "cites"
    assert classify_citation_direction(None, None) == "cites"


def test_same_year_is_plain_citation():
    assert classify_citation_direction(2024, 2024) == "cites"


# --------------------------------------------------------------------------
# OpenAlex referansları
# --------------------------------------------------------------------------

def test_openalex_refs_normalised():
    refs = normalize_openalex_refs([
        "https://openalex.org/W2741809807",
        "W123",
        "not-an-id",
        None,
    ])
    assert refs == ["W2741809807", "W123"]


def test_non_list_refs_ignored():
    assert normalize_openalex_refs(None) == []
    assert normalize_openalex_refs("W1") == []


# --------------------------------------------------------------------------
# Kəsişmələr
# --------------------------------------------------------------------------

def test_author_overlap_survives_format_differences():
    shared = author_overlap(["Yann LeCun", "G. Hinton"], ["LeCun, Yann", "Y. Bengio"])
    assert "lecun" in shared


def test_no_author_overlap():
    assert author_overlap(["Alice Cooper"], ["Bob Dylan"]) == set()


def test_method_overlap_is_case_insensitive():
    a = {"methods": ["Transformer", "Adam"]}
    b = {"methods": ["transformer", "SGD"]}
    assert method_overlap(a, b) == {"transformer"}


def test_method_overlap_handles_missing_insights():
    assert method_overlap({}, {"methods": ["x"]}) == set()
    assert method_overlap(None, None) == set()


# --------------------------------------------------------------------------
# Xülasə
# --------------------------------------------------------------------------

def test_summary_separates_facts_from_derived():
    """İnterfeys faktı mühakimədən ayıra bilməlidir — xülasə də ayırır."""
    rows = [
        {"relation": "cites", "confidence": 1.0},
        {"relation": "cites", "confidence": 1.0},
        {"relation": "related_to", "confidence": 0.62},
        {"relation": "same_authors", "confidence": 0.7},
    ]
    s = summarize_relations(rows)
    assert s["total"] == 4
    assert s["verified"] == 2      # yalnız sitatlar
    assert s["derived"] == 2
    assert s["by_type"]["cites"] == 2


def test_empty_summary():
    s = summarize_relations([])
    assert s["total"] == 0 and s["by_type"] == {}


def test_relation_types_cover_the_spec():
    """§15-in sadaladığı tiplər mövcud olmalıdır."""
    for required in ("cites", "builds_on", "extends", "supports",
                     "contradicts", "replicates", "uses_method", "related_to"):
        assert required in RELATION_TYPES


# --------------------------------------------------------------------------
# Müəllif açarı — canlı icrada tapılan səhv
# --------------------------------------------------------------------------

def test_author_key_includes_first_initial():
    """REGRESSION: yalnız soyadla uyğunlaşdıranda 1 596 məqalədən 5 551
    `same_authors` əlaqəsi yarandı — məqalə başına ~3.5.

    Səbəb: «Wang», «Li», «Zhang» kimi soyadlar onlarla məqalədə təkrarlanır.
    Əlaqə «eyni adam» yox, «eyni soyad» deməyə başlamışdı.
    """
    from app.relations import author_keys

    assert author_keys(["Yann LeCun"]) == {"y.lecun"}
    assert author_keys(["LeCun, Yann"]) == {"y.lecun"}


def test_different_people_with_same_surname_do_not_match():
    assert author_overlap(["Wei Wang"], ["Yan Wang"]) == set()
    assert author_overlap(["Wei Wang"], ["Wei Wang"]) == {"wang"}


def test_missing_initial_is_not_evidence_against():
    """Yoxluq sübut deyil — dedup-dakı `has_conflicting_ids` ilə eyni prinsip."""
    assert author_overlap(["Wang"], ["Wei Wang"]) == {"wang"}


def test_abbreviated_first_name_still_matches():
    assert author_overlap(["Y. LeCun"], ["Yann LeCun"]) == {"lecun"}
