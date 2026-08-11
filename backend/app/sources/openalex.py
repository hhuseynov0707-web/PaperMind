"""OpenAlex — çoxdilli elmi işlər reyestri (rusdilli məqalələr üçün əsas mənbə).

Diqqət: OpenAlex-in `language` etiketi səhv ola bilər (ingiliscə iş `ru`
işarələnə bilər), ona görə çəkiləndən sonra mətnin əlifbası yoxlanılır.
Həmçinin User-Agent olmadan API boş nəticə qaytarır («nəzakətli hovuz»).
"""

import time
from datetime import date, datetime, timezone

import requests

from ..config import settings
from .common import detect_language, normalize_doi, usable

API = "https://api.openalex.org/works"
CS_FIELD = "fields/17"          # Computer Science
PAGE = 50
RATE_LIMIT_S = 1.2

# Sahə açarı -> rusca axtarış terminləri (OpenAlex `|` işarəsini OR kimi qəbul edir)
FIELD_TERMS_RU: dict[str, list[str]] = {
    "ai": ["машинное обучение", "нейронная сеть", "искусственный интеллект"],
    "cv": ["компьютерное зрение", "распознавание образов", "обработка изображений"],
    "security": ["кибербезопасность", "защита информации", "криптография"],
    "robotics": ["робототехника", "мобильный робот", "управление роботом"],
    "software": ["разработка программного обеспечения", "тестирование программ"],
    "data": ["база данных", "информационный поиск", "обработка данных"],
    "networks": ["компьютерные сети", "беспроводные сети", "сетевой протокол"],
    "hci": ["человеко-машинный интерфейс", "пользовательский интерфейс"],
}


def _headers() -> dict:
    ua = "PaperMind/1.0 (Scientific Intelligence Platform)"
    if settings.contact_email:
        ua += f"; mailto:{settings.contact_email}"
    return {"User-Agent": ua}


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
    external_id = doi or (work.get("id") or "").rsplit("/", 1)[-1]
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
        "arxiv_id": None,
        "doi": doi,
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
          timeout: int = 45, lang: str = "ru") -> list[dict]:
    terms = FIELD_TERMS_RU.get(field_key, []) if lang == "ru" else []
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
        resp = requests.get(API, params=params, headers=_headers(), timeout=timeout)
        resp.raise_for_status()
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
