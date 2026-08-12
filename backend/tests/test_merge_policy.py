"""Birləşmə siyasəti — audit D1-in regression testləri.

Tapılan səhv: `_find_existing` üç açarı `or_` ilə yoxlayırdı, ona görə DOI-ları
FƏRQLİ olan iki ayrı iş eyni başlığa görə birləşirdi. §4 bunu qadağan edir.

Bu testlər DB tələb etmir — qərar məntiqi bilərəkdən saf funksiyalara ayrılıb.
"""

import pytest

from app.sources.common import has_conflicting_ids, title_merge_allowed


# --------------------------------------------------------------------------
# Ziddiyyətli identifikatorlar
# --------------------------------------------------------------------------

def test_different_dois_conflict():
    assert has_conflicting_ids({"doi": "10.1/a"}, {"doi": "10.2/b"}) is True


def test_same_doi_no_conflict():
    assert has_conflicting_ids({"doi": "10.1/a"}, {"doi": "10.1/a"}) is False


def test_missing_doi_is_not_conflict():
    """Məlumatın yoxluğu ziddiyyət deyil — arXiv preprint-in DOI-su olmaya bilər."""
    assert has_conflicting_ids({"arxiv_id": "2601.00001"}, {"doi": "10.1/a"}) is False
    assert has_conflicting_ids({"doi": "10.1/a"}, {}) is False


def test_different_arxiv_ids_conflict():
    assert has_conflicting_ids({"arxiv_id": "2601.00001"}, {"arxiv_id": "2601.00002"}) is True


# --------------------------------------------------------------------------
# D1 — əsas regression
# --------------------------------------------------------------------------

def test_title_merge_blocked_when_dois_differ():
    """D1 REGRESSION: eyni başlıq + fərqli DOI = FƏRQLİ işlər, birləşməməlidir."""
    assert title_merge_allowed(
        {"doi": "10.1000/aaa"}, ["Ivanov I."],
        {"doi": "10.2000/bbb"}, ["Ivanov I."],
    ) is False


def test_title_merge_blocked_when_arxiv_ids_differ():
    assert title_merge_allowed(
        {"arxiv_id": "2601.00001"}, ["Smith J."],
        {"arxiv_id": "2601.00002"}, ["Smith J."],
    ) is False


def test_preprint_to_published_still_merges():
    """Vacib: düzəliş legitim birləşməni POZMAMALIDIR.

    arXiv preprint-in DOI-su yoxdur, jurnal versiyasının arXiv ID-si yoxdur —
    ziddiyyət yaranmır, müəlliflər eynidir, ona görə birləşməlidir.
    """
    assert title_merge_allowed(
        {"arxiv_id": "2601.00001"}, ["Yann LeCun", "Geoffrey Hinton"],
        {"doi": "10.1038/nature14539"}, ["LeCun, Yann", "Hinton, Geoffrey"],
    ) is True


def test_same_title_different_authors_blocked():
    """"Introduction to Machine Learning" kimi başlıqlar müxtəlif işlərdə təkrarlanır."""
    assert title_merge_allowed(
        {}, ["Alice Cooper"],
        {}, ["Bob Dylan"],
    ) is False


def test_shared_surname_is_enough():
    """Bir müəllif üst-üstə düşsə kifayətdir — mənbələr siyahını fərqli kəsir."""
    assert title_merge_allowed(
        {}, ["A. Nasirov", "B. Qasimov"],
        {}, ["Nasirov, Aydin", "C. Mammadov"],
    ) is True


def test_missing_authors_does_not_block():
    """Müəllif məlumatı olmayan tərəf varsa, yoxluq sübut kimi işlədilmir."""
    assert title_merge_allowed({}, [], {}, ["Ivanov I."]) is True
    assert title_merge_allowed({}, ["Ivanov I."], {}, []) is True


def test_author_format_differences_tolerated():
    """"Yann LeCun" / "LeCun, Yann" / "Y. LeCun" eyni adam sayılmalıdır."""
    assert title_merge_allowed(
        {}, ["Y. LeCun"],
        {}, ["LeCun, Yann"],
    ) is True


# --------------------------------------------------------------------------
# D2 — giriş həddi
# --------------------------------------------------------------------------

def test_oversized_abstract_rejected():
    """§17: limitsiz abstract chunker-i və embedding-i partladır."""
    from pydantic import ValidationError

    from app.schemas import MAX_ABSTRACT, PaperIn

    with pytest.raises(ValidationError):
        PaperIn(title="Normal başlıq", abstract="x" * (MAX_ABSTRACT + 1), arxiv_id="2601.00001")


def test_oversized_title_rejected():
    from pydantic import ValidationError

    from app.schemas import MAX_TITLE, PaperIn

    with pytest.raises(ValidationError):
        PaperIn(title="x" * (MAX_TITLE + 1), abstract="normal", arxiv_id="2601.00001")


def test_huge_author_list_truncated_not_rejected():
    """CERN məqalələrində 3000+ müəllif olur — məqalə İTİRİLMƏMƏLİDİR."""
    from app.schemas import MAX_AUTHORS, PaperIn

    p = PaperIn(
        title="ATLAS kollaborasiyası nəticələri",
        abstract="normal abstract",
        arxiv_id="2601.00001",
        authors=[f"Author {i}" for i in range(3000)],
    )
    assert len(p.authors) == MAX_AUTHORS


def test_absurd_author_name_truncated():
    from app.schemas import MAX_ITEM, PaperIn

    p = PaperIn(
        title="Test məqaləsi",
        abstract="normal abstract",
        arxiv_id="2601.00001",
        authors=["A" * 100_000],
    )
    assert len(p.authors[0]) == MAX_ITEM


def test_oversized_batch_rejected():
    from pydantic import ValidationError

    from app.schemas import MAX_BATCH, IngestBatch, PaperIn

    one = PaperIn(title="Test məqaləsi", abstract="abstract", arxiv_id="2601.00001")
    with pytest.raises(ValidationError):
        IngestBatch(papers=[one] * (MAX_BATCH + 1))


# --------------------------------------------------------------------------
# D7 — PMID və OpenAlex ID (§4)
# --------------------------------------------------------------------------

def test_pmid_normalization():
    from app.sources.common import normalize_pmid

    assert normalize_pmid("PMID: 12345678") == "12345678"
    assert normalize_pmid("https://pubmed.ncbi.nlm.nih.gov/12345678/") == "12345678"
    assert normalize_pmid("12345678") == "12345678"
    assert normalize_pmid("") is None
    assert normalize_pmid(None) is None


def test_openalex_id_normalization():
    from app.sources.common import normalize_openalex_id

    assert normalize_openalex_id("https://openalex.org/W2741809807") == "W2741809807"
    assert normalize_openalex_id("w2741809807") == "W2741809807"
    assert normalize_openalex_id("not-an-id") is None
    assert normalize_openalex_id(None) is None


def test_different_pmids_conflict():
    assert has_conflicting_ids({"pmid": "111"}, {"pmid": "222"}) is True


def test_different_openalex_ids_conflict():
    assert has_conflicting_ids({"openalex_id": "W1"}, {"openalex_id": "W2"}) is True


def test_pmid_conflict_blocks_title_merge():
    """Tibb korpusunda PMID DOI qədər güclü açardır."""
    assert title_merge_allowed(
        {"pmid": "111"}, ["Ivanov I."],
        {"pmid": "222"}, ["Ivanov I."],
    ) is False


def test_paper_accepts_pmid_only_identity():
    """Europe PMC bəzi qeydləri DOI-suz verir — PMID kimlik üçün kifayət etməlidir."""
    from app.schemas import PaperIn

    p = PaperIn(title="Klinik tədqiqat nəticələri", abstract="abstract", pmid="12345678")
    assert p.external_id == "12345678"


# --------------------------------------------------------------------------
# D6 — abstrakt zənginləşdirmə
# --------------------------------------------------------------------------

def test_fuller_abstract_replaces_truncated():
    """arXiv kəsik abstrakt verir, Crossref tam versiyanı — yaxşısı qalmalıdır."""
    from app.crud import _better_abstract

    short = "Bu iş haqqında qısa məlumat." * 2
    full = short * 3
    assert _better_abstract(short, full) == full


def test_marginally_different_abstract_ignored():
    """Kiçik fərq üçün chunk-ları yenidən hesablamaq baha başa gəlir."""
    from app.crud import _better_abstract

    a = "x" * 1000
    assert _better_abstract(a, "x" * 1050) is None
    assert _better_abstract(a, a) is None


def test_shorter_abstract_never_wins():
    from app.crud import _better_abstract

    assert _better_abstract("x" * 1000, "x" * 100) is None


def test_missing_current_abstract_filled():
    from app.crud import _better_abstract

    assert _better_abstract(None, "yeni abstrakt") == "yeni abstrakt"
    assert _better_abstract("mövcud", None) is None


# --------------------------------------------------------------------------
# Mənbə körpüsü — OpenAlex-dən arXiv ID (§3, §4)
# --------------------------------------------------------------------------

def test_openalex_extracts_arxiv_id_from_landing_page():
    """Preprint ↔ nəşr birləşməsi yalnız bu ID ilə mümkündür: arXiv qeydlərinin
    əksəriyyətində DOI yoxdur, ona görə OpenAlex körpü rolunu oynayır."""
    from app.sources.openalex import _arxiv_from_locations

    work = {"locations": [
        {"landing_page_url": "https://arxiv.org/abs/2601.01234"},
        {"landing_page_url": "https://doi.org/10.1/x"},
    ]}
    assert _arxiv_from_locations(work) == "2601.01234"


def test_openalex_extracts_arxiv_id_from_pdf_url():
    from app.sources.openalex import _arxiv_from_locations

    work = {"locations": [{"pdf_url": "http://arxiv.org/pdf/2512.09876v2"}]}
    assert _arxiv_from_locations(work) == "2512.09876"


def test_openalex_no_arxiv_link_returns_none():
    from app.sources.openalex import _arxiv_from_locations

    assert _arxiv_from_locations({"locations": [{"landing_page_url": "https://nature.com/x"}]}) is None
    assert _arxiv_from_locations({}) is None
