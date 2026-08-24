"""Statik qiymət səhifəsi — §18.

`static/pricing.html` qiyməti BİRBAŞA HTML-də saxlayır, JavaScript işlətmir.
Səbəb praktikdir: qiymət yalnız modal pəncərədə və `/api/auth/plans` sorğusundan
sonra görünürdü, yəni JS işlətməyən hər kəs — ödəniş provayderinin yoxlayıcısı,
axtarış botu, mətn brauzeri — heç bir qiymət görmürdü.

Bunun bədəli ikinci həqiqət mənbəyidir: rəqəm həm `config.py`-də, həm HTML-də.
Şablonlaşdırma bütöv render qatı tələb edərdi (və səhifəni yenidən JS-dən
asılı edərdi), ona görə əvəzində DREYFİ TEST TUTUR. Qiymət dəyişəndə bu
testlər düşür və HTML-i yeniləməyi unutmaq mümkün olmur.
"""

import io
import re
from pathlib import Path

import pytest

from app.config import settings

PAGE = Path(__file__).resolve().parents[1] / "app" / "static" / "pricing.html"


@pytest.fixture(scope="module")
def html() -> str:
    return io.open(PAGE, encoding="utf-8").read()


def test_page_exists():
    assert PAGE.is_file(), f"{PAGE} yoxdur"


# --- Ən vacib: qiymət JS OLMADAN görünür ----------------------------------

def test_price_is_in_the_raw_html(html):
    """Bütün səhifənin mövcudluq səbəbi budur.

    `$3` xam HTML-də olmasa, səhifə heç nə həll etmir — əvvəlki vəziyyətlə
    eyni olur.
    """
    assert settings.pro_price_label in html, (
        f"{settings.pro_price_label!r} pricing.html-də tapılmadı — "
        "config.py dəyişib, səhifə yenilənməyib"
    )


def test_page_needs_no_javascript(html):
    """`<script>` olsa, qiymətin görünməsi yenə JS-dən asılı ola bilər."""
    assert "<script" not in html.lower()


def test_free_plan_shows_zero(html):
    assert "$0" in html


# --- config.py ilə uyğunluq ------------------------------------------------

def test_credits_match_config(html):
    """Kredit rəqəmləri də dreyf edə bilər — plan limiti dəyişəndə səhifə
    köhnə rəqəmi göstərməyə davam edərdi."""
    assert str(settings.pro_monthly_credits) in html
    assert str(settings.free_monthly_credits) in html


def test_library_limits_match_config(html):
    assert str(settings.pro_library_limit) in html
    assert str(settings.free_library_limit) in html


def test_no_stale_price_numbers(html):
    """Səhifədə göstərilən HƏR dollar rəqəmi ya pulsuz plandır, ya da
    konfiqurasiyadakı Pro qiymətidir. Üçüncü bir rəqəm qalıbsa, o,
    yeniləməkdən unudulmuş köhnə qiymətdir."""
    found = set(re.findall(r"\$\d+(?:\.\d+)?", html))
    allowed = {"$0", settings.pro_price_label}
    assert found <= allowed, f"gözlənilməyən qiymət rəqəmi: {found - allowed}"


# --- Ödəniş provayderinin tələbləri ---------------------------------------

@pytest.mark.parametrize("href", ["/terms.html", "/privacy.html", "/refunds.html"])
def test_links_to_legal_pages(html, href):
    """Paddle-ın açıq tələbi: sayt terms, privacy və refund siyasətinə
    keçid verməlidir."""
    assert href in html


def test_says_who_handles_payment(html):
    """Satıcı qeydiyyatlı reseller-dir; istifadəçi hesabında hansı adı
    görəcəyini əvvəlcədən bilməlidir."""
    assert "Paddle" in html


def test_mentions_cancellation_and_refunds(html):
    low = html.lower()
    assert "cancel" in low
    assert "refund" in low
