import hashlib
import re

from .. import cache
from ..config import settings
from ..security import translation_budget_ok
from .llm import translate_to_english

_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
_AZ_CHARS = re.compile(r"[əƏıİğĞşŞçÇöÖüÜ]")

# Diakritiksiz yazılmış Azərbaycan mətnini tutmaq üçün birmənalı sözlər
# (ingiliscə ilə toqquşmayan formalar seçilib)
_AZ_ASCII_HINTS = {
    "nedir", "necedir", "hansi", "hansilar", "hansilardir", "ucun", "uchun",
    "niye", "neden", "haqqinda", "barede", "meqale", "meqaleler", "movzu",
    "movzular", "yanasma", "yanasmalar", "usullar", "olarmi", "varmi",
    "sistemlerde", "modellerde", "axtaris", "cavab", "suallar", "izah",
}


def detect_lang(text: str) -> str:
    """Sadə heuristika: kiril → ru, Azərbaycan hərfləri/sözləri → az, qalanı → en."""
    if _CYRILLIC.search(text):
        return "ru"
    if _AZ_CHARS.search(text):
        return "az"
    tokens = set(re.findall(r"[a-z]+", text.lower()))
    if tokens & _AZ_ASCII_HINTS:
        return "az"
    return "en"


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
