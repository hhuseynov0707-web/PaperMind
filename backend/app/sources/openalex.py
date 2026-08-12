"""OpenAlex — çoxdilli elmi işlər reyestri (rusdilli məqalələr üçün əsas mənbə).

Diqqət: OpenAlex-in `language` etiketi səhv ola bilər (ingiliscə iş `ru`
işarələnə bilər), ona görə çəkiləndən sonra mətnin əlifbası yoxlanılır.
Həmçinin User-Agent olmadan API boş nəticə qaytarır («nəzakətli hovuz»).
"""

import re
import time
from datetime import date, datetime, timezone

import requests

from ..config import settings
from .common import (
    detect_language,
    get_with_retry,
    normalize_doi,
    normalize_openalex_id,
    normalize_pmid,
    usable,
)

API = "https://api.openalex.org/works"
CS_FIELD = "fields/17"          # Computer Science
PAGE = 50
RATE_LIMIT_S = 1.2

# Sahə açarı -> rusca axtarış terminləri (OpenAlex `|` işarəsini OR kimi qəbul edir)
FIELD_TERMS_RU: dict[str, list[str]] = {
    # texnologiya
    "ai": ["машинное обучение", "нейронная сеть", "искусственный интеллект"],
    "cv": ["компьютерное зрение", "распознавание образов", "обработка изображений"],
    "security": ["кибербезопасность", "защита информации", "криптография"],
    "robotics": ["робототехника", "мобильный робот", "управление роботом"],
    "software": ["разработка программного обеспечения", "тестирование программ"],
    "data": ["база данных", "информационный поиск", "обработка данных"],
    "networks": ["компьютерные сети", "беспроводные сети", "сетевой протокол"],
    "hci": ["человеко-машинный интерфейс", "пользовательский интерфейс"],

    # təbiət elmləri
    "physics": ["квантовая механика", "физика конденсированного состояния", "элементарные частицы"],
    "astronomy": ["астрофизика", "космология", "звёздная эволюция"],
    "chemistry": ["органический синтез", "катализ", "химическая реакция"],
    "biology": ["молекулярная биология", "экспрессия генов", "структура белка"],
    "earth": ["изменение климата", "геофизика", "атмосферные процессы"],

    # formal elmlər
    "math": ["численные методы", "теория оптимизации", "теория вероятностей", "теория графов"],
    "statistics": ["статистический анализ", "байесовский подход", "регрессионная модель"],

    # tibb və sağlamlıq
    "medicine": ["клиническое исследование", "диагностика и лечение", "общественное здоровье"],
    "neuroscience": ["нейробиология", "нейровизуализация", "когнитивные функции"],

    # sosial elmlər
    "economics": ["экономический рост", "денежно-кредитная политика", "финансовый риск"],
    "psychology": ["когнитивная психология", "психическое здоровье", "поведение человека"],
}


def _headers() -> dict:
    ua = "PaperMind/1.0 (Scientific Intelligence Platform)"
    if settings.contact_email:
        ua += f"; mailto:{settings.contact_email}"
    return {"User-Agent": ua}


_ARXIV_URL = re.compile(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5})", re.IGNORECASE)


def _arxiv_from_locations(work: dict) -> str | None:
    """OpenAlex qeydindən arXiv ID-ni çıxarır.

    OpenAlex `ids` blokunda arXiv ID vermir, amma preprint versiyası
    `locations[].landing_page_url` və ya `pdf_url` sahəsində arxiv.org linki
    kimi görünür. Bu ID olmadan arXiv preprinti ilə jurnal versiyası heç vaxt
    birləşə bilmir (arXiv qeydlərinin əksəriyyətində DOI yoxdur).
    """
    for loc in (work.get("locations") or []):
        for key in ("landing_page_url", "pdf_url"):
            m = _ARXIV_URL.search(loc.get(key) or "")
            if m:
                return m.group(1)
    return None


def _abstract(inverted: dict | None) -> str | None:
    """OpenAlex abstraktı tərs indeks kimi saxlayır — mətnə çevirir."""
    if not inverted:
        return None
    positions: dict[int, str] = {}
    for word, idxs in inverted.items():
        for i in idxs:
            positions[i] = word
    if not positions:
        return None
    return " ".join(positions[k] for k in sorted(positions))


def _parse(work: dict, field_key: str, want_lang: str) -> dict | None:
    title = " ".join((work.get("title") or "").split())
    abstract = _abstract(work.get("abstract_inverted_index"))
    if not usable(title, abstract):
        return None

    # Etiketə yox, mətnin əlifbasına güvənirik
    lang = detect_language(title, abstract)
    if lang != want_lang:
        return None

    doi = normalize_doi(work.get("doi"))
    # OpenAlex work id-si onsuz da gəlirdi, amma yalnız external_id üçün işlədilib
    # atılırdı. İndi kanonik açar kimi saxlanılır (§4): DOI-suz işləri — çoxdilli
    # korpusda bunlar azlıq təşkil etmir — mənbələr arası bağlamağa imkan verir.
    openalex_id = normalize_openalex_id(work.get("id"))
    # PMID OpenAlex-də ids blokunda gəlir; tibb korpusu üçün ən güclü açardır
    pmid = normalize_pmid((work.get("ids") or {}).get("pmid"))
    # arXiv ID OpenAlex-in `ids` blokunda gəlmir, amma `locations` içindəki
    # arxiv.org linkindən çıxarıla bilir. Bu, preprint ↔ nəşr birləşməsini
    # mümkün edən yeganə siqnaldır: arXiv qeydlərinin əksəriyyətində DOI yoxdur.
    arxiv_id = _arxiv_from_locations(work)
    external_id = doi or openalex_id
    if not external_id:
        return None

    published = None
    if work.get("publication_date"):
        try:
            published = datetime.fromisoformat(work["publication_date"]).replace(tzinfo=timezone.utc)
        except ValueError:
            published = None

    authors = []
    for a in work.get("authorships") or []:
        name = ((a.get("author") or {}).get("display_name") or "").strip()
        if name:
            authors.append(name)

    return {
        "source": "openalex",
        "external_id": external_id,
        "arxiv_id": arxiv_id,
        "doi": doi,
        "pmid": pmid,
        "openalex_id": openalex_id,
        "title": title,
        "abstract": abstract,
        "authors": authors[:20],
        "published_at": published,
        "pdf_url": work.get("doi") or work.get("id"),
        "primary_category": None,
        "categories": [],
        "field_keys": [field_key],
        "language": lang,
    }


def fetch(field_key: str, since: date, limit: int = 100,
          timeout: int = 90, lang: str = "ru") -> list[dict]:
    # Əvvəllər `lang != "ru"` olanda boş qayıdırdı, yəni OpenAlex yalnız rusdilli
    # mənbə idi. Halbuki o, həm arXiv preprintlərini, həm jurnal nəşrlərini
    # indeksləyən yeganə mənbədir — yəni korpusu bir-birinə bağlayan körpüdür
    # (§3, §4). İngiliscə terminlər digər mənbələrlə eyni siyahıdan gəlir ki,
    # sahə tərifi bir yerdə qalsın.
    if lang == "ru":
        terms = FIELD_TERMS_RU.get(field_key, [])
    else:
        from . import FIELD_TERMS
        terms = FIELD_TERMS.get(field_key, [])
    if not terms:
        return []
    search = "|".join(terms)

    out: list[dict] = []
    cursor = "*"
    while len(out) < limit:
        params = {
            "filter": (
                f"title_and_abstract.search:{search},"
                f"language:{lang},has_abstract:true,"
                f"from_publication_date:{since.isoformat()}"
            ),
            "per-page": min(PAGE, max(limit - len(out), 1)),
            "cursor": cursor,
            "sort": "publication_date:desc",
        }
        resp = get_with_retry(API, params=params, headers=_headers(), timeout=timeout)
        data = resp.json()
        results = data.get("results") or []
        if not results:
            break

        for work in results:
            parsed = _parse(work, field_key, lang)
            if parsed:
                out.append(parsed)

        cursor = (data.get("meta") or {}).get("next_cursor")
        if not cursor:
            break
        time.sleep(RATE_LIMIT_S)

    return out[:limit]
