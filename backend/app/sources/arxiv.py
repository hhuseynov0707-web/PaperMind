"""arXiv Atom API — preprintlər (mövcud mənbə, ortaq interfeysə uyğunlaşdırılıb)."""

import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone

import requests

from ..fields import FIELDS
from .common import clean_abstract, get_with_retry, normalize_arxiv_id, usable

API = "http://export.arxiv.org/api/query"
NS = {"a": "http://www.w3.org/2005/Atom"}
PAGE = 100
RATE_LIMIT_S = 3.0          # arXiv qaydası: sorğular arasında ən azı 3 saniyə


def _parse_entry(entry: ET.Element, field_key: str) -> dict | None:
    def txt(tag: str) -> str:
        el = entry.find(f"a:{tag}", NS)
        return (el.text or "").strip() if el is not None and el.text else ""

    raw_id = txt("id")
    arxiv_id = normalize_arxiv_id(raw_id)
    title = " ".join(txt("title").split())
    abstract = clean_abstract(txt("summary"))
    if not arxiv_id or not usable(title, abstract):
        return None

    cats = [c.attrib.get("term", "") for c in entry.findall("a:category", NS)]
    cats = [c for c in cats if c]
    primary_el = entry.find("{http://arxiv.org/schemas/atom}primary_category")
    primary = primary_el.attrib.get("term") if primary_el is not None else (cats[0] if cats else None)

    published = None
    if txt("published"):
        try:
            published = datetime.fromisoformat(txt("published").replace("Z", "+00:00"))
        except ValueError:
            published = None

    pdf_url = next(
        (l.attrib.get("href") for l in entry.findall("a:link", NS)
         if l.attrib.get("title") == "pdf"),
        raw_id or None,
    )

    # arXiv-də sahə kateqoriyalardan çıxarılır — sorğu sahəsi yox, real təsnifat
    derived = {k for k, codes in FIELDS.items() if set(codes) & set(cats)}
    doi_el = entry.find("{http://arxiv.org/schemas/atom}doi")

    return {
        "source": "arxiv",
        "external_id": arxiv_id,
        "arxiv_id": arxiv_id,
        "doi": doi_el.text.strip() if doi_el is not None and doi_el.text else None,
        "title": title,
        "abstract": abstract,
        "authors": [
            (a.findtext("a:name", default="", namespaces=NS) or "").strip()
            for a in entry.findall("a:author", NS)
        ],
        "published_at": published,
        "pdf_url": pdf_url,
        "primary_category": primary,
        "categories": cats,
        "field_keys": sorted(derived or {field_key}),
    }


def fetch(field_key: str, since: date, limit: int = 200,
          timeout: int = 120, lang: str = "en") -> list[dict]:
    """Sahəyə uyğun arXiv kateqoriyalarından `since` tarixindən sonrakı məqalələr.

    arXiv praktiki olaraq yalnız ingiliscədir — başqa dil istənsə boş qaytarır.
    """
    if lang != "en":
        return []
    codes = FIELDS.get(field_key, [])
    if not codes:
        return []
    query = "+OR+".join(f"cat:{c}" for c in codes)

    out: list[dict] = []
    start = 0
    while len(out) < limit:
        url = (
            f"{API}?search_query={query}&start={start}&max_results={PAGE}"
            "&sortBy=submittedDate&sortOrder=descending"
        )
        resp = get_with_retry(url, timeout=timeout, headers={"User-Agent": "PaperMind/1.0"})
        entries = ET.fromstring(resp.text).findall("a:entry", NS)
        if not entries:
            break

        stop = False
        for entry in entries:
            item = _parse_entry(entry, field_key)
            if not item:
                continue
            pub = item["published_at"]
            if pub and pub.date() < since:
                stop = True
                continue
            out.append(item)
        if stop or len(entries) < PAGE:
            break
        start += PAGE
        time.sleep(RATE_LIMIT_S)

    return out[:limit]
