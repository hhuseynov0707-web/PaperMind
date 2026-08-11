"""DOAJ API — açıq girişli, resenziyadan keçmiş jurnal məqalələri."""

import time
from datetime import date, datetime, timezone
from urllib.parse import quote

import requests

from .common import clean_abstract, detect_language, get_with_retry, normalize_doi, usable

API = "https://doaj.org/api/search/articles"
PAGE = 100
RATE_LIMIT_S = 1.0


def _parse(article: dict, field_key: str, want_lang: str = "en") -> dict | None:
    bib = article.get("bibjson") or {}
    title = " ".join((bib.get("title") or "").split())
    abstract = clean_abstract(bib.get("abstract"))
    if not usable(title, abstract):
        return None

    # Jurnalın dil etiketi deyil, mətnin öz əlifbası həlledicidir:
    # rus jurnalları çox vaxt ingiliscə abstrakt dərc edir.
    lang = detect_language(title, abstract)
    if lang != want_lang:
        return None

    doi = None
    url = None
    for ident in bib.get("identifier") or []:
        if ident.get("type") == "doi":
            doi = normalize_doi(ident.get("id"))
    for link in bib.get("link") or []:
        if link.get("type") == "fulltext":
            url = link.get("url")

    published = None
    year, month = bib.get("year"), bib.get("month")
    if year:
        try:
            published = datetime(int(year), int(month or 1), 1, tzinfo=timezone.utc)
        except (TypeError, ValueError):
            published = None

    external_id = doi or article.get("id")
    if not external_id:
        return None

    return {
        "source": "doaj",
        "external_id": external_id,
        "arxiv_id": None,
        "doi": doi,
        "title": title,
        "abstract": abstract,
        "authors": [a.get("name", "").strip() for a in (bib.get("author") or []) if a.get("name")],
        "published_at": published,
        "pdf_url": url or (f"https://doi.org/{doi}" if doi else None),
        "primary_category": None,
        "categories": [],
        "field_keys": [field_key],
        "language": lang,
    }


def fetch(field_key: str, since: date, limit: int = 200,
          timeout: int = 90, lang: str = "en") -> list[dict]:
    from . import FIELD_TERMS
    from .openalex import FIELD_TERMS_RU

    terms = (FIELD_TERMS_RU if lang == "ru" else FIELD_TERMS).get(field_key, [])
    if not terms:
        return []

    # DOAJ Elasticsearch sintaksisi: terminlərdən biri başlıq və ya abstraktda olsun
    ors = " OR ".join(f'"{t}"' for t in terms)
    query = f'(bibjson.title:({ors}) OR bibjson.abstract:({ors}))'

    out: list[dict] = []
    page = 1
    while len(out) < limit:
        url = f"{API}/{quote(query, safe='')}"
        params = {"pageSize": min(PAGE, limit - len(out)), "page": page, "sort": "created_date:desc"}
        resp = get_with_retry(url, params=params, timeout=timeout,
                              headers={"User-Agent": "PaperMind/1.0"})
        results = resp.json().get("results") or []
        if not results:
            break

        stop = False
        for article in results:
            parsed = _parse(article, field_key, lang)
            if not parsed:
                continue
            pub = parsed["published_at"]
            if pub and pub.date() < since:
                stop = True          # created_date üzrə sıralı — köhnəyə çatdıq
                continue
            out.append(parsed)

        if stop or len(results) < params["pageSize"]:
            break
        page += 1
        time.sleep(RATE_LIMIT_S)

    return out[:limit]
