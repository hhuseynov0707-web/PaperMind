"""Çoxmənbəli ilk dolduruş: arXiv + Crossref + DOAJ.

İstifadə (konteynerin içindən):
    docker compose exec backend python scripts/backfill_multi.py --days 14 --limit 80
    docker compose exec backend python scripts/backfill_multi.py --sources crossref,doaj

Mövcud `backfill.py` yalnız arXiv üçün qalır; bu skript hamısını gəzir və
deduplikasiya backend-də (crud.upsert_papers) baş verir.
"""

import argparse
import json
import sys
import urllib.request

API = "http://localhost:8000/api/ingest/pull"
ALL_SOURCES = ["arxiv", "crossref", "doaj"]


def pull(source: str, fields: list[str], days: int, limit: int, timeout: int = 900) -> dict:
    payload = json.dumps({
        "source": source, "fields": fields,
        "days": days, "limit_per_field": limit,
    }).encode()
    req = urllib.request.Request(API, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14, help="neçə gün geriyə (maks 60)")
    ap.add_argument("--limit", type=int, default=80, help="hər sahə üçün maksimum məqalə")
    ap.add_argument("--sources", default=",".join(ALL_SOURCES))
    ap.add_argument("--fields", default="", help="boş = bütün sahələr")
    args = ap.parse_args()

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    fields = [f.strip() for f in args.fields.split(",") if f.strip()]

    totals = {"fetched": 0, "inserted": 0, "skipped": 0, "merged": 0}
    for source in sources:
        print(f"\n=== {source} (son {args.days} gün, sahə başına {args.limit}) …", flush=True)
        try:
            res = pull(source, fields, args.days, args.limit)
        except Exception as exc:
            print(f"  XƏTA: {exc}", file=sys.stderr)
            continue
        for k in totals:
            totals[k] += res.get(k, 0)
        print(f"  yeni={res['inserted']}  təkrar={res['skipped']}  birləşdirilən={res['merged']}")
        for field, n in sorted(res.get("per_field", {}).items(), key=lambda x: -x[1]):
            if n:
                print(f"    {field:10s} {n}")

    print(
        f"\nYEKUN: {totals['inserted']} yeni · {totals['skipped']} təkrar · "
        f"{totals['merged']} başqa mənbədə tapılıb birləşdirildi"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
