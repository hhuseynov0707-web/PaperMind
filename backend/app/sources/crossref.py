"""Crossref REST API — nəşr olunmuş jurnal/konfrans məqalələri (DOI-nin rəsmi reyestri)."""

import time
from datetime import date, datetime, timezone

import requests

from ..config import settings
from .common import clean_abstract, normalize_doi, usable

API = "https://api.crossref.org/works"
PAGE = 100
RATE_LIMIT_S = 1.0
TYPES = "journal-article,proceedings-article"


def _headers() -> dict:
    """Crossref «nəzakətli hovuz»u əlaqə e-poçtu olan User-Agent istəyir."""
    ua = "PaperMind/1.0 (Scientific Intelligence Platform)"
    if settings.contact_email:
        ua += f"; mailto:{settings.contact_email}"
    return {"User-Agent": ua}


def _parse(item: dict, field_key: str) -> dict | None:
    doi = normalize_doi(item.get("DOI"))
    titles = item.get("title") or []
    title = " ".join((titles[0] if titles else "").split())
    abstract = clean_abstract(item.get("abstract"))
    if not doi or not usable(title, abstract):
        return None

    published = None
    parts = (item.get("published") or {}).get("date-parts") or []
    if parts and parts[0]:
        y, m, d = (list(parts[0]) + [1, 1])[:3]
        try:
            published = datetime(int(y), int(m or 1), int(d or 1), tzinfo=timezone.utc)
        except (TypeError, ValueError):
            published = None

    authors = []
    for a in item.get("author") or []:
        name = " ".join(x for x in [a.get("given"), a.get("family")] if x).strip()
        if name:
            authors.append(name)

    return {
        "source": "crossref",
        "external_id": doi,
        "arxiv_id": None,
        "doi": doi,
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "published_at": published,
        "pdf_url": item.get("URL") or f"https://doi.org/{doi}",
        "primary_category": None,
        "categories": [],
        "field_keys": [field_key],
    }


def fetch(field_key: str, since: date, limit: int = 200,
          timeout: int = 45, lang: str = "en") -> list[dict]:
    from . import FIELD_TERMS

    if lang != "en":          # rusdilli məqalələr üçün openalex/doaj işlədilir
        return []
    terms = FIELD_TERMS.get(field_key, [])
    if not terms:
        return []

    out: list[dict] = []
    cursor = "*"
    while len(out) < limit:
        params = {
            "query.bibliographic": " ".join(terms),
            "filter": f"has-abstract:true,from-pub-date:{since.isoformat()},type:{TYPES.split(',')[0]}",
            "rows": min(PAGE, limit - len(out)),
            "cursor": cursor,
            "select": "DOI,title,abstract,author,published,URL,type",
            "sort": "published",
            "order": "desc",
        }
        resp = requests.get(API, params=params, headers=_headers(), timeout=timeout)
        resp.raise_for_status()
        msg = resp.json().get("message", {})
        items = msg.get("items") or []
        if not items:
            break

        for item in items:
            parsed = _parse(item, field_key)
            if parsed:
                out.append(parsed)

        cursor = msg.get("next-cursor")
        if not cursor or len(items) < params["rows"]:
            break
        time.sleep(RATE_LIMIT_S)

    return out[:limit]
