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
    assert has_conflicting_ids("10.1/a", None, "10.2/b", None) is True


def test_same_doi_no_conflict():
    assert has_conflicting_ids("10.1/a", None, "10.1/a", None) is False


def test_missing_doi_is_not_conflict():
    """Məlumatın yoxluğu ziddiyyət deyil — arXiv preprint-in DOI-su olmaya bilər."""
    assert has_conflicting_ids(None, "2601.00001", "10.1/a", None) is False
    assert has_conflicting_ids("10.1/a", None, None, None) is False


def test_different_arxiv_ids_conflict():
    assert has_conflicting_ids(None, "2601.00001", None, "2601.00002") is True


# --------------------------------------------------------------------------
# D1 — əsas regression
# --------------------------------------------------------------------------

def test_title_merge_blocked_when_dois_differ():
    """D1 REGRESSION: eyni başlıq + fərqli DOI = FƏRQLİ işlər, birləşməməlidir."""
    assert title_merge_allowed(
        "10.1000/aaa", None, ["Ivanov I."],
        "10.2000/bbb", None, ["Ivanov I."],
    ) is False


def test_title_merge_blocked_when_arxiv_ids_differ():
    assert title_merge_allowed(
        None, "2601.00001", ["Smith J."],
        None, "2601.00002", ["Smith J."],
    ) is False


def test_preprint_to_published_still_merges():
    """Vacib: düzəliş legitim birləşməni POZMAMALIDIR.

    arXiv preprint-in DOI-su yoxdur, jurnal versiyasının arXiv ID-si yoxdur —
    ziddiyyət yaranmır, müəlliflər eynidir, ona görə birləşməlidir.
    """
    assert title_merge_allowed(
        None, "2601.00001", ["Yann LeCun", "Geoffrey Hinton"],
        "10.1038/nature14539", None, ["LeCun, Yann", "Hinton, Geoffrey"],
    ) is True


def test_same_title_different_authors_blocked():
    """"Introduction to Machine Learning" kimi başlıqlar müxtəlif işlərdə təkrarlanır."""
    assert title_merge_allowed(
        None, None, ["Alice Cooper"],
        None, None, ["Bob Dylan"],
    ) is False


def test_shared_surname_is_enough():
    """Bir müəllif üst-üstə düşsə kifayətdir — mənbələr siyahını fərqli kəsir."""
    assert title_merge_allowed(
        None, None, ["A. Nasirov", "B. Qasimov"],
        None, None, ["Nasirov, Aydin", "C. Mammadov"],
    ) is True


def test_missing_authors_does_not_block():
    """Müəllif məlumatı olmayan tərəf varsa, yoxluq sübut kimi işlədilmir."""
    assert title_merge_allowed(None, None, [], None, None, ["Ivanov I."]) is True
    assert title_merge_allowed(None, None, ["Ivanov I."], None, None, []) is True


def test_author_format_differences_tolerated():
    """"Yann LeCun" / "LeCun, Yann" / "Y. LeCun" eyni adam sayılmalıdır."""
    assert title_merge_allowed(
        None, None, ["Y. LeCun"],
        None, None, ["LeCun, Yann"],
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
