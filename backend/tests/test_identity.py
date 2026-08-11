"""Deduplikasiya açarları və dil təyini.

Bu funksiyalar sistemin ən kritik hissəsidir: səssizcə sınsalar, eyni məqalə
təkrar-təkrar göstərilməyə başlayar və ya rusdilli korpus yanlış təsnif olunar.
Heç biri xəta vermir — sadəcə yanlış nəticə qaytarır. Ona görə test lazımdır.
"""

import pytest

from app.sources.common import (
    clean_abstract,
    detect_language,
    normalize_arxiv_id,
    normalize_doi,
    title_key,
    usable,
)


# ------------------------------------------------------------------ DOI

@pytest.mark.parametrize("raw,expected", [
    ("10.1145/3576915", "10.1145/3576915"),
    ("https://doi.org/10.1145/3576915", "10.1145/3576915"),
    ("http://dx.doi.org/10.1145/3576915", "10.1145/3576915"),
    ("doi:10.1145/3576915", "10.1145/3576915"),
    ("  10.1145/3576915  ", "10.1145/3576915"),
    ("10.1145/3576915.", "10.1145/3576915"),      # sondakı nöqtə
    ("10.1145/ABC123", "10.1145/abc123"),          # reqistr
    ("", None),
    (None, None),
])
def test_doi_normalizasiyasi(raw, expected):
    assert normalize_doi(raw) == expected


def test_eyni_doi_ferqli_yazilislar_uygun_gelir():
    """Crossref DOI-nı prefikssiz, OpenAlex isə tam URL kimi verir."""
    assert normalize_doi("10.1000/XYZ") == normalize_doi("https://doi.org/10.1000/xyz")


# ------------------------------------------------------------------ arXiv ID

@pytest.mark.parametrize("raw,expected", [
    ("2608.01234", "2608.01234"),
    ("2608.01234v2", "2608.01234"),               # versiya eyni məqalədir
    ("arXiv:2608.01234", "2608.01234"),
    ("http://arxiv.org/abs/2608.01234v3", "2608.01234"),
    ("", None),
    (None, None),
])
def test_arxiv_id_normalizasiyasi(raw, expected):
    assert normalize_arxiv_id(raw) == expected


# ------------------------------------------------------------------ başlıq açarı

def test_eyni_baslik_ferqli_yazilis_eyni_acar():
    a = title_key("Attention Is All You Need")
    b = title_key("attention is all you need")
    c = title_key("Attention, is all you need!")
    d = title_key("  Attention   Is  All   You  Need  ")
    assert a == b == c == d
    assert a is not None


def test_diakritika_acari_deyismir():
    assert title_key("Uber die Struktur") == title_key("Über die Strüktür")


def test_ferqli_bashliqlar_ferqli_acar():
    assert title_key("Deep learning for vision") != title_key("Deep learning for speech")


def test_cox_qisa_bashliq_acar_vermir():
    """Qısa başlıqlar yanlış birləşməyə səbəb olardı — qəsdən None qaytarılır."""
    assert title_key("AI") is None
    assert title_key("Notes") is None


# ------------------------------------------------------------------ dil

def test_kiril_metn_rusca_sayilir():
    assert detect_language("Машинное обучение и нейронные сети") == "ru"


def test_latin_metn_ingiliscə_sayilir():
    assert detect_language("Machine learning and neural networks") == "en"


def test_qarisiq_metnde_coxluq_qalib_gelir():
    """Rus jurnalları başlığa ingiliscə termin qatır — mətnin çoxu həlledicidir."""
    assert detect_language("Криптографическая защита информации (cryptography)") == "ru"
    assert detect_language("A survey of методы in modern systems research") == "en"


def test_bosh_metn_ingiliscə_sayilir():
    assert detect_language("", None) == "en"


def test_bashliq_ve_abstrakt_birlikde_qiymetlendirilir():
    assert detect_language("Java", "Библиотека для работы с кривыми") == "ru"


# ------------------------------------------------------------------ abstrakt

def test_jats_xml_temizlenir():
    raw = "<jats:p>Network pharmacology is a <jats:italic>growing</jats:italic> area.</jats:p>"
    assert clean_abstract(raw) == "Network pharmacology is a growing area."


def test_html_entity_acilir():
    assert clean_abstract("Cost &lt; 5% &amp; fast") == "Cost < 5% & fast"


def test_bashdaki_abstract_sozu_atilir():
    assert clean_abstract("Abstract This paper presents").startswith("This paper")


def test_bosh_abstrakt_none_qaytarir():
    assert clean_abstract("") is None
    assert clean_abstract("<jats:p></jats:p>") is None


# ------------------------------------------------------------------ yararlılıq

def test_qisa_abstrakt_qebul_edilmir():
    """Abstraktsız qeyd RAG üçün dəyərsizdir — embedding etməyə dəyməz."""
    assert usable("Yaxşı başlıq", "Çox qısa.") is False


def test_bashliqsiz_qeyd_qebul_edilmir():
    assert usable("", "x" * 400) is False
    assert usable(None, "x" * 400) is False


def test_normal_qeyd_qebul_edilir():
    assert usable("Real başlıq", "x" * 250) is True
