"""İlk dolduruş: arXiv-dən son N günün məqalələrini çəkib /api/ingest-ə göndərir.

İstifadə (konteynerin içindən):
    docker compose exec backend python scripts/backfill.py --days 30

arXiv qaydası: sorğular arasında ən azı 3 saniyə fasilə (rəsmi tələb).
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import feedparser
import requests

ARXIV_URL = "http://export.arxiv.org/api/query"
API_URL = os.environ.get("BACKFILL_API_URL", "http://localhost:8000/api/ingest")
PAGE_SIZE = 100


def entry_to_paper(e) -> dict:
    raw_id = e.get("id", "")
    m = re.search(r"/abs/(.+)$", raw_id)
    arxiv_id = re.sub(r"v\d+$", "", m.group(1)) if m else raw_id

    tags = [t.get("term") for t in e.get("tags", []) if t.get("term")]
    primary = (e.get("arxiv_primary_category") or {}).get("term") or (tags[0] if tags else None)

    return {
        "arxiv_id": arxiv_id,
        "title": re.sub(r"\s+", " ", e.get("title", "")).strip(),
        "abstract": re.sub(r"\s+", " ", e.get("summary", "")).strip(),
        "primary_category": primary,
        "categories": tags,
        "authors": [a.get("name") for a in e.get("authors", []) if a.get("name")],
        "published_at": e.get("published"),
        "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}",
    }


def fetch_page(search_query: str, start: int) -> list:
    params = {
        "search_query": search_query,
        "start": start,
        "max_results": PAGE_SIZE,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    for attempt in range(3):
        try:
            resp = requests.get(ARXIV_URL, params=params, timeout=30)
            resp.raise_for_status()
            return feedparser.parse(resp.content).entries
        except requests.RequestException as exc:
            print(f"  arXiv sorğusu alınmadı (cəhd {attempt + 1}/3): {exc}")
            time.sleep(5)
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="arXiv backfill")
    parser.add_argument("--days", type=int, default=30, help="Neçə günlük məqalə çəkilsin")
    parser.add_argument("--max-pages", type=int, default=15, help="Maksimum səhifə sayı (təhlükəsizlik limiti)")
    parser.add_argument(
        "--categories",
        default="cs.AI,cs.LG,cs.CL,cs.NE,stat.ML,cs.CV,eess.IV,cs.CR,cs.RO,cs.SY,eess.SY,cs.SE,cs.PL,cs.DB,cs.IR,cs.DC,cs.NI,cs.OS,cs.AR,cs.HC,cs.CY",
        help="Vergüllə ayrılmış arXiv kateqoriyaları (default: bütün texnologiya sahələri)",
    )
    args = parser.parse_args()

    search_query = " OR ".join(f"cat:{c.strip()}" for c in args.categories.split(","))
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    print(f"Hədəf: {args.categories} | son {args.days} gün (>= {cutoff.date()})")

    papers, start, reached_cutoff = [], 0, False
    for page in range(args.max_pages):
        entries = fetch_page(search_query, start)
        if not entries:
            break
        for e in entries:
            p = entry_to_paper(e)
            if p["published_at"]:
                published = datetime.fromisoformat(p["published_at"].replace("Z", "+00:00"))
                if published < cutoff:
                    reached_cutoff = True
                    break
            if p["arxiv_id"] and p["abstract"]:
                papers.append(p)
        print(f"Səhifə {page + 1}: cəmi {len(papers)} məqalə yığıldı")
        if reached_cutoff:
            break
        start += PAGE_SIZE
        time.sleep(3)  # arXiv rate limit qaydası

    if not papers:
        print("Heç nə tapılmadı — kateqoriyaları və interneti yoxla.")
        return 1

    total_inserted = total_skipped = 0
    for i in range(0, len(papers), 100):
        batch = papers[i : i + 100]
        resp = requests.post(API_URL, json={"papers": batch}, timeout=300)
        resp.raise_for_status()
        result = resp.json()
        total_inserted += result["inserted"]
        total_skipped += result["skipped"]
        print(f"  Batch {i // 100 + 1}: inserted={result['inserted']}, skipped={result['skipped']}")

    print(f"\nNəticə: {total_inserted} yeni, {total_skipped} təkrar (idempotent ötürüldü)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
