"""Mənbələr arasında ortaq normallaşdırma və deduplikasiya açarları.

Eyni məqalə arXiv-də preprint, Crossref-də DOI-lu nəşr, DOAJ-da açıq giriş
versiyası kimi görünə bilər. Üç açar üzrə eyniləşdirilir:
  1) DOI            — ən güclü, nəşrçi tərəfindən verilir
  2) arXiv ID       — preprint eyniliyi
  3) başlıq açarı   — preprint ↔ nəşr cütlərini tutur (DOI fərqli olanda)
"""

import hashlib
import html
import logging
import re
import time
import unicodedata

import requests

log = logging.getLogger("papermind.sources")

# Xarici akademik API-lər qeyri-sabitdir: arXiv geniş sorğularda yavaşlayır,
# Crossref/OpenAlex isə yüklənmə anlarında 5xx qaytarır. Bir timeout bütöv
# sahəni itirməsin deyə sorğular geri çəkilmə ilə təkrarlanır.
RETRY_STATUSES = {429, 500, 502, 503, 504}


def get_with_retry(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = 90,
    attempts: int = 3,
    backoff: float = 4.0,
) -> requests.Response:
    """GET sorğusu; timeout və müvəqqəti server xətalarında təkrar cəhd edir.

    Son cəhd də uğursuz olarsa istisna qaldırılır — çağıran tərəf onu
    error_logs-a yazır və digər sahələrə davam edir.
    """
    last: Exception | None = None
    for i in range(attempts):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code in RETRY_STATUSES and i < attempts - 1:
                wait = backoff * (i + 1)
                log.warning("%s → HTTP %s, %.0f san sonra təkrar", url, resp.status_code, wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except (requests.Timeout, requests.ConnectionError) as exc:
            last = exc
            if i < attempts - 1:
                wait = backoff * (i + 1)
                log.warning("%s → %s, %.0f san sonra təkrar", url, type(exc).__name__, wait)
                time.sleep(wait)
    raise last if last else RuntimeError(f"{url}: bütün cəhdlər uğursuz")

_DOI_PREFIXES = ("https://doi.org/", "http://doi.org/", "http://dx.doi.org/", "doi:")
_JATS_TAG = re.compile(r"<[^>]+>")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_ARXIV_VERSION = re.compile(r"v\d+$")


def normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    d = doi.strip().lower()
    for pref in _DOI_PREFIXES:
        if d.startswith(pref):
            d = d[len(pref):]
            break
    d = d.strip().rstrip(".")
    return d or None


def normalize_arxiv_id(value: str | None) -> str | None:
    """`arXiv:2608.01234v2` → `2608.01234` (versiya eyni məqalədir)."""
    if not value:
        return None
    v = value.strip().lower()
    if v.startswith("arxiv:"):
        v = v[6:]
    v = v.rsplit("/abs/", 1)[-1]
    v = _ARXIV_VERSION.sub("", v)
    return v or None


def title_key(title: str | None) -> str | None:
    """Başlığı deduplikasiya açarına çevirir: diakritika, durğu işarəsi və boşluqdan asılı olmayan hash."""
    if not title:
        return None
    t = unicodedata.normalize("NFKD", html.unescape(title))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = _NON_ALNUM.sub(" ", t).strip()
    if len(t) < 12:            # çox qısa başlıqlar yanlış birləşmə yaradır
        return None
    return hashlib.sha1(" ".join(t.split()).encode()).hexdigest()


def clean_abstract(raw: str | None) -> str | None:
    """Crossref JATS XML-ini və HTML qalıqlarını təmiz mətnə çevirir."""
    if not raw:
        return None
    text = _JATS_TAG.sub(" ", raw)
    text = html.unescape(text)
    text = " ".join(text.split())
    if text.lower().startswith("abstract "):
        text = text[9:]
    return text or None


def usable(title: str | None, abstract: str | None, min_abstract: int = 200) -> bool:
    """RAG üçün yararlılıq: abstrakt olmayan qeydlər embedding üçün dəyərsizdir."""
    return bool(title and title.strip()) and bool(abstract) and len(abstract) >= min_abstract


_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")
_LATIN_RE = re.compile(r"[A-Za-z]")


def detect_language(*parts: str | None) -> str:
    """Mətnin dilini əlifbaya görə təyin edir: 'ru' | 'en'.

    Mənbələrin `language` etiketi etibarsızdır — rus jurnalları çox vaxt
    ingiliscə abstrakt verir, OpenAlex isə bəzi ingiliscə işləri `ru`
    işarələyir. Ona görə mətnin ÖZÜNƏ baxılır.
    """
    text = " ".join(p for p in parts if p)
    if not text:
        return "en"
    cyr = len(_CYRILLIC_RE.findall(text))
    lat = len(_LATIN_RE.findall(text))
    return "ru" if cyr > lat else "en"
