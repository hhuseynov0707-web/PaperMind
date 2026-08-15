import hashlib
import re

from .. import cache
from ..config import settings
from ..security import translation_budget_ok
from .llm import translate_to_english

_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
_AZ_CHARS = re.compile(r"[əƏıİğĞşŞçÇöÖüÜ]")

# Diakritikasız yazılan Azərbaycan mətni ÖLÇÜLDÜ və problem çıxdı: istifadəçi
# «mene oxumaqa ne vere bilersen» yazanda sistem onu ingiliscə sayır və cavabı
# ingiliscə verirdi. Köhnə siyahıda cəmi 24 söz var idi və bu cümlədəki heç bir
# sözü tutmurdu.
#
# İndi iki siqnal işlədilir: FUNKSİYA SÖZLƏRİ və ŞƏKİLÇİLƏR. Şəkilçilər vacibdir,
# çünki lüğət heç vaxt tam olmur — «kompyuterlerde» sözü siyahıda yoxdur, amma
# `-lerde` şəkilçisi onu tutur.

# Güclü göstəricilər: ingiliscə ilə toqquşmayan sözlər (hər biri 2 xal)
_AZ_WORDS = {
    "nedir", "necedir", "nece", "hansi", "hansilar", "hansilardir", "ucun",
    "uchun", "niye", "neden", "haqqinda", "barede", "meqale", "meqaleler",
    "movzu", "movzular", "yanasma", "usul", "usullar", "olarmi", "varmi",
    "axtaris", "cavab", "sual", "suallar", "izah", "komek", "komeyi",
    "bilersen", "bilerem", "bilir", "edirsen", "edirem", "eder", "ede",
    "vere", "verer", "verirsen", "goster", "gosterir", "danis", "danisaq",
    "oxumaq", "oxumaqa", "oxuyaq", "yazmaq", "tapmaq", "tapa", "isleyir",
    "iseleyir", "islemir", "salam", "sagol", "tesekkur", "zehmet", "olmasa",
    "mene", "sene", "bize", "size", "onlara", "menim", "senin", "bizim",
    "bunlar", "bunlari", "onlarin", "hamisi", "bezi", "daha", "yaxsi",
    "lazim", "lazimdir", "deyil", "yoxdur", "vardir", "gore", "kimi",
    "ile", "ve", "amma", "ancaq", "yoxsa", "eger", "cunki", "sonra", "evvel",
    "indi", "burada", "orada", "harada", "hara", "kim", "kimdir", "nedi",
}

# Şəkilçilər: lüğətdə olmayan sözləri də tutur (hər biri 1 xal)
_AZ_SUFFIXES = (
    "dir", "dur", "lar", "ler", "lari", "leri", "larin", "lerin",
    "dan", "den", "da", "de", "nin", "nun", "sen", "san", "iram", "irem",
    "mek", "maq", "misdir", "acaq", "ecek", "irik", "iriq", "diki",
)

# Bu qədər xal toplansa `az` sayılır. 2 seçilib: bir güclü söz VƏ YA iki
# şəkilçi kifayətdir, amma təsadüfi bir şəkilçi tək başına kifayət etmir
# (ingiliscə «under», «leader» kimi sözlər yanlış müsbət verməsin).
_AZ_SCORE_THRESHOLD = 2

_FOLD_AZ = str.maketrans({
    "ə": "e", "Ə": "e", "ğ": "g", "Ğ": "g", "ı": "i", "İ": "i",
    "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u",
    "ç": "c", "Ç": "c",
})


def _az_score(text: str) -> int:
    """Azərbaycan dili göstəricilərinin xalı."""
    folded = (text or "").translate(_FOLD_AZ).lower()
    tokens = re.findall(r"[a-z]+", folded)
    score = 0
    for tok in tokens:
        if tok in _AZ_WORDS:
            score += 2
        elif len(tok) > 4 and tok.endswith(_AZ_SUFFIXES):
            score += 1
    return score


def detect_lang(text: str) -> str:
    """Sorğunun dili: 'ru' | 'az' | 'en'.

    Kiril → rus. Azərbaycan hərfləri → az. Diakritika yoxdursa xal hesablanır
    (funksiya sözləri + şəkilçilər), çünki istifadəçilər çox vaxt «ə, ı, ş»
    yazmır və köhnə 24 sözlük siyahı onların əksəriyyətini tutmurdu.
    """
    if _CYRILLIC.search(text or ""):
        return "ru"
    if _AZ_CHARS.search(text or ""):
        return "az"
    return "az" if _az_score(text) >= _AZ_SCORE_THRESHOLD else "en"


def retrieval_inputs(text: str) -> tuple[str, str | None, str, str | None]:
    """Retrieval üçün (əsas sorğu, əlavə vektor, dil, tərcümə) qaytarır.

    Strategiya dilə görə fərqlidir — benchmark ilə ölçülüb (n=60, korpus 1047):

        dil   əsas        əlavə      səbəb
        ---   ---------   --------   ---------------------------------------
        en    orijinal    —          tərcümə olunmur
        ru    orijinal    tərcümə    orijinal sahə dəqiqliyini 63%→72% qaldırır,
                                     tərcümə known-item MRR-i 0.70→0.80
        az    tərcümə     —          azərbaycanca vektor səs-küy əlavə edir:
                                     yalnız tərcümə 60%, orijinal qoşulanda 52%

    Bu funksiya həm axtarış/RAG, həm də benchmark tərəfindən çağırılır ki,
    ölçdüyümüz davranışla istifadəçinin gördüyü davranış eyni olsun.
    """
    query_en, lang = query_to_english(text)

    if lang == "en":
        return text, None, lang, None
    if lang == "az":
        return query_en, None, lang, query_en
    return text, query_en, lang, query_en


def query_to_english(text: str) -> tuple[str, str]:
    """(ingiliscə sorğu, aşkarlanmış dil) qaytarır.

    Korpus ingiliscə abstraktlardan ibarətdir və embedding modeli ingiliscə
    mətndə güclüdür — ona görə az/ru sorğular embedding-dən ƏVVƏL Groq ilə
    ingiliscəyə çevrilir. Tərcümələr Redis-də 7 gün keşlənir; tərcümə
    alınmasa, orijinal sorğu ilə davam edilir.
    """
    lang = detect_lang(text)
    if lang == "en" or not settings.groq_api_key:
        return text, lang

    key = f"tr:{hashlib.sha256(text.strip().lower().encode()).hexdigest()}"
    cached = cache.get_json(key)
    if cached:
        return cached, lang

    # Keşdə yoxdursa bu, REAL LLM çağırışıdır — qlobal günlük tavana tabedir
    # (audit S3). Tavan dolubsa orijinal sorğu ilə davam edirik.
    if not translation_budget_ok():
        return text, lang

    try:
        translated = translate_to_english(text)
    except Exception:
        return text, lang

    cache.set_json(key, translated, 7 * 86400)
    return translated, lang
