"""Sorğu anlama — §6 testləri.

Auditdə W6: sorğudan yalnız dil çıxarılırdı. Bu testlər niyyət, müəllif və
tarix çıxarışını yoxlayır — hamısı saf funksiyalardır, LLM tələb etmir.
"""

from datetime import date

from app.rag.understanding import (
    INTENT_ROUTE,
    INTENTS,
    detect_intents,
    extract_authors,
    extract_years,
    fold,
    strip_constraints,
    understand,
)

TODAY = date(2026, 8, 13)


# --------------------------------------------------------------------------
# Diakritika — real istifadəçi yazılışı
# --------------------------------------------------------------------------

def test_diacritics_folded_to_ascii():
    assert fold("FƏRQ") == "ferq"
    assert fold("mövzu") == "movzu"
    assert fold("əlaqə") == "elaqe"
    assert fold("İstiqamət") == "istiqamet"


def test_intent_works_with_and_without_diacritics():
    """İstifadəçilər «fərq» yerinə «ferq» yazır — hər iki forma tanınmalıdır.

    Nümunələr diakritika ilə yazılsaydı, sorğuların çoxu SEARCH-ə düşərdi.
    """
    assert understand("transformer ilə RNN arasındakı fərq").intent == "COMPARE"
    assert understand("transformer ile RNN arasindaki ferq").intent == "COMPARE"
    assert understand("fizikada hansı mövzular yeni yaranır").intent == "EMERGING_TOPIC"
    assert understand("fizikada hansi movzular yeni yaranir").intent == "EMERGING_TOPIC"


# --------------------------------------------------------------------------
# Niyyət
# --------------------------------------------------------------------------

def test_each_intent_detected_in_three_languages():
    cases = [
        ("CONTRADICTION", "ziddiyyətli nəticələr", "противоречивые результаты",
         "conflicting findings"),
        ("RESEARCH_GAP", "hansı boşluqlar var", "какие пробелы",
         "what is the research gap"),
        ("EMERGING_TOPIC", "yeni yaranan mövzular", "новое направление",
         "emerging topics"),
        ("CROSS_DISCIPLINARY", "fənlərarası əlaqələr", "междисциплинарные связи",
         "cross-disciplinary links"),
        ("TREND", "zamanla necə dəyişib", "как изменилось со временем",
         "how has it changed over time"),
        ("COMPARE", "müqayisə et", "сравнить методы", "compare these methods"),
        ("EXPLAIN", "bu nədir", "что такое это", "what is this"),
    ]
    for expected, az, ru, en in cases:
        for text in (az, ru, en):
            assert understand(text).intent == expected, f"{expected}: {text}"


def test_plain_query_stays_search():
    assert understand("attention mechanism for long documents").intent == "SEARCH"
    assert understand("kvant hesablama").intent == "SEARCH"


def test_specific_intent_wins_over_general():
    """«Ziddiyyətli nəticələri müqayisə et» — CONTRADICTION daha dardır."""
    plan = understand("ziddiyyətli nəticələri müqayisə et")
    assert plan.intent == "CONTRADICTION"
    assert "COMPARE" in plan.intents


def test_comparison_between_two_things_is_not_cross_disciplinary():
    """«X ilə Y arasındakı fərq» müqayisədir, fənlərarası sorğu deyil.

    İlk versiya «arasında» sözünü tək başına fənlərarası sayırdı.
    """
    assert understand("transformer ilə RNN arasındakı fərq").intent == "COMPARE"
    assert understand("statistik mexanika ilə maliyyə arasındakı əlaqə").intent == "CROSS_DISCIPLINARY"


def test_every_intent_has_a_route():
    for intent in INTENTS:
        assert intent in INTENT_ROUTE


# --------------------------------------------------------------------------
# Müəllif
# --------------------------------------------------------------------------

def test_single_word_author():
    assert extract_authors("author:LeCun attention mechanism") == ["LeCun"]


def test_quoted_multiword_author():
    assert extract_authors('author:"Yann LeCun" transformer') == ["Yann LeCun"]


def test_unquoted_author_does_not_swallow_the_query():
    """REGRESSION: ilk versiya `[^\\n,;]+` işlədirdi və bütün sorğunu ad kimi
    udurdu — filtr yanlış olurdu, axtarış mətni isə boşalırdı."""
    plan = understand("author:LeCun attention mechanism")
    assert plan.authors == ["LeCun"]
    assert plan.core == "attention mechanism"


def test_author_prefix_in_three_languages():
    assert extract_authors("müəllif:Nəsirov") == ["Nəsirov"]
    assert extract_authors("автор:Иванов") == ["Иванов"]


def test_no_author_prefix_means_no_filter():
    """Sərbəst ad tanıma qəsdən yoxdur: «Monte Carlo» müəllif kimi tutulardı."""
    assert extract_authors("Monte Carlo simulation of Markov chains") == []


# --------------------------------------------------------------------------
# Tarix
# --------------------------------------------------------------------------

def test_year_range():
    assert extract_years("nəticələr 2020-2023 arasında", TODAY) == (2020, 2023)


def test_reversed_year_range_normalised():
    assert extract_years("2023-2020", TODAY) == (2020, 2023)


def test_relative_years_in_three_languages():
    assert extract_years("son 3 il", TODAY) == (2024, 2026)
    assert extract_years("за последние 5 лет", TODAY) == (2022, 2026)
    assert extract_years("last 2 years", TODAY) == (2025, 2026)


def test_since_year():
    assert extract_years("since 2019", TODAY) == (2019, 2026)


def test_single_year():
    assert extract_years("attention 2017", TODAY) == (2017, 2017)


def test_no_year_means_no_filter():
    assert extract_years("attention mechanism", TODAY) == (None, None)


def test_numbers_that_are_not_years_ignored():
    """«top 50 methods» tarix məhdudiyyəti deyil."""
    assert extract_years("top 50 methods for 3d rendering", TODAY) == (None, None)


# --------------------------------------------------------------------------
# Təmizlənmiş sorğu
# --------------------------------------------------------------------------

def test_constraints_removed_from_search_text():
    """Məhdudiyyət ifadəsi embedding üçün səs-küydür — filtr kimi işlədilir,
    mətndən isə çıxarılır."""
    plan = understand('author:"Yann LeCun" transformer architecture son 3 il', TODAY)
    assert plan.core == "transformer architecture"
    assert plan.authors == ["Yann LeCun"]
    assert plan.year_from == 2024


def test_core_never_empty():
    """Sorğu tamamilə məhdudiyyətdən ibarətdirsə, orijinala qayıdırıq —
    boş mətnlə axtarış mənasızdır."""
    plan = understand("author:LeCun", TODAY)
    assert plan.core


def test_plan_serialises():
    plan = understand("compare these two methods")
    data = plan.as_dict()
    assert data["intent"] == "COMPARE"
    assert "core" in data and "authors" in data
