"""Retrieval keyfiyyətinin ölçülməsi.

Niyə lazımdır: «axtarış yaxşı işləyir» gözlə yoxlamaqla təsdiqlənə bilməz.
Model, çəkilər və ya retrieval strategiyası dəyişəndə nəyin yaxşılaşdığını,
nəyin pisləşdiyini yalnız ölçmə göstərir. (Bu skript yazılmazdan əvvəl
rusca sorğuların rusdilli korpusu tamamilə gözdən qaçırdığı aylarla
görünməyə bilərdi.)

Üç ölçmə:

  1. KNOWN-ITEM — bazadan təsadüfi məqalə götürülür, BAŞLIĞI sorğu kimi
     verilir və həmin məqalənin öz abstraktının tapılıb-tapılmadığına baxılır.
     Başlıq chunk-lara daxil edilmir (yalnız abstrakt vektorlaşdırılır), ona
     görə bu, süni asan tapşırıq deyil.  Ölçü: MRR@10, Recall@10.

  2. SAHƏ DƏQİQLİYİ — əl ilə yazılmış sorğular (eval/queries.json), hər birinin
     gözlənilən sahəsi var. Nəticələrin neçə faizinin həmin sahəyə aid olduğu
     ölçülür.  Ölçü: Precision@10.

  3. ÇARPAZ DİLLİ ƏHATƏ — rusca sorğularda nəticələrin neçə faizinin rusdilli
     məqalə olduğu. Korpus əsasən ingiliscədir, ona görə bu, sıfırdan böyük
     olmalıdır — sıfır olsa, rusdilli korpus görünmür deməkdir.

İstifadə:
    docker compose exec backend python scripts/benchmark.py
    docker compose exec backend python scripts/benchmark.py --compare
    docker compose exec backend python scripts/benchmark.py --sample 40
"""

import argparse
import json
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, "/app")

from sqlalchemy import func, select                    # noqa: E402
from app.config import settings                        # noqa: E402
from app.database import SessionLocal                  # noqa: E402
from app.models import Paper                           # noqa: E402
from app.rag.retriever import retrieve                 # noqa: E402
from app.rag.translator import query_to_english        # noqa: E402

QUERIES = Path(__file__).resolve().parent.parent / "eval" / "queries.json"
K = 10
CHUNK_POOL = 40          # chunk səviyyəsində çəkilir, sonra məqalə üzrə dedup


def top_papers(db, query: str, k: int = K, also: str | None = None,
               field: str | None = None) -> list[Paper]:
    """Retrieval nəticələrini məqalə səviyyəsində təkrarsız qaytarır."""
    blocks = retrieve(db, query, top_k=CHUNK_POOL,
                      categories=[field] if field else None, also=also)
    seen, out = set(), []
    for b in blocks:
        p = b["paper"]
        if p.id in seen:
            continue
        seen.add(p.id)
        out.append(p)
        if len(out) >= k:
            break
    return out


# ----------------------------------------------------------------- 1. known-item

def _prepare(text: str, mode: str) -> tuple[str, str | None]:
    """Rejimə görə (əsas sorğu, əlavə vektor) qaytarır.

    both       — orijinal + tərcümə (cari davranış)
    original   — yalnız orijinal
    translated — YALNIZ tərcümə (düzəlişdən əvvəlki davranış)
    """
    if mode == "original":
        return text, None
    translated, lang = query_to_english(text)
    if lang == "en":
        return text, None
    if mode == "translated":
        return translated, None
    return text, translated


def known_item(db, sample: int, mode: str, seed: int = 7) -> dict:
    rng = random.Random(seed)
    results: dict[str, list[float]] = {"en": [], "ru": []}
    latencies: list[float] = []

    for lang in ("en", "ru"):
        # ORDER BY vacibdir: onsuz Postgres sıra qaydasına zəmanət vermir,
        # eyni seed fərqli nümunə verir və nəticələr müqayisə oluna bilmir.
        ids = db.scalars(
            select(Paper.id).where(Paper.language == lang).order_by(Paper.id)
        ).all()
        if not ids:
            continue
        picked = rng.sample(ids, min(sample, len(ids)))
        for pid in picked:
            paper = db.get(Paper, pid)
            if not paper or not paper.title:
                continue
            query, also = _prepare(paper.title, mode)

            t0 = time.perf_counter()
            found = top_papers(db, query, also=also)
            latencies.append((time.perf_counter() - t0) * 1000)

            rank = next((i + 1 for i, p in enumerate(found) if p.id == pid), 0)
            results[lang].append(1.0 / rank if rank else 0.0)

    return {
        "per_lang": {
            lang: {
                "n": len(v),
                "mrr": statistics.mean(v) if v else 0.0,
                "recall": sum(1 for x in v if x > 0) / len(v) if v else 0.0,
            }
            for lang, v in results.items() if v
        },
        "latency_ms": statistics.median(latencies) if latencies else 0.0,
    }


# ------------------------------------------------------- 2/3. sahə + çarpaz dilli

def field_precision(db, mode: str) -> dict:
    spec = json.loads(QUERIES.read_text(encoding="utf-8"))
    by_lang: dict[str, list[float]] = {}
    ru_share: list[float] = []
    per_field: dict[str, list[float]] = {}

    for item in spec["field_queries"]:
        q, lang, want = item["q"], item["lang"], item["field"]
        query, also = _prepare(q, mode)
        papers = top_papers(db, query, also=also)
        if not papers:
            continue
        hit = sum(1 for p in papers if want in (p.field_keys or [])) / len(papers)
        by_lang.setdefault(lang, []).append(hit)
        per_field.setdefault(want, []).append(hit)
        if lang == "ru":
            ru_share.append(sum(1 for p in papers if p.language == "ru") / len(papers))

    return {
        "by_lang": {k: statistics.mean(v) for k, v in by_lang.items()},
        "by_field": {k: statistics.mean(v) for k, v in sorted(per_field.items())},
        "ru_share": statistics.mean(ru_share) if ru_share else 0.0,
    }


# ----------------------------------------------------------------- hesabat

def run(db, sample: int, mode: str) -> dict:
    return {
        "known": known_item(db, sample, mode),
        "field": field_precision(db, mode),
    }


def show(label: str, r: dict) -> None:
    print(f"\n  {label}")
    print("  " + "-" * 52)
    for lang, m in r["known"]["per_lang"].items():
        print(f"    known-item {lang}   MRR@10 {m['mrr']:.3f}   "
              f"Recall@10 {m['recall']:.0%}   (n={m['n']})")
    print(f"    median latency    {r['known']['latency_ms']:.0f} ms")
    for lang, v in sorted(r["field"]["by_lang"].items()):
        print(f"    sahə dəqiqliyi {lang}   P@10 {v:.0%}")
    print(f"    rusca sorğu → rusdilli nəticə payı   {r['field']['ru_share']:.0%}")


def main() -> int:
    ap = argparse.ArgumentParser()
    # n=25-də bir məqalənin 1-ci sıradan 3-cüyə düşməsi MRR-i 0.027 dəyişir —
    # konfiqurasiyalar arasındakı real fərqdən böyük səs-küy. 60 daha sabitdir.
    ap.add_argument("--sample", type=int, default=60, help="dil başına known-item sayı")
    ap.add_argument("--compare", action="store_true",
                    help="tərcümə vektoru ilə və onsuz müqayisə et")
    args = ap.parse_args()

    db = SessionLocal()
    total = db.scalar(select(func.count(Paper.id))) or 0
    print("PaperMind — retrieval benchmark")
    print("=" * 56)
    print(f"  model  : {settings.embedding_model}")
    print(f"  korpus : {total} məqalə")

    current = run(db, args.sample, "both")
    show("ORİJİNAL + TƏRCÜMƏ (cari davranış)", current)

    if args.compare:
        show("YALNIZ ORİJİNAL SORĞU", run(db, args.sample, "original"))

        legacy = run(db, args.sample, "translated")
        show("YALNIZ TƏRCÜMƏ (düzəlişdən əvvəlki davranış)", legacy)

        print("\n  " + "=" * 52)
        print("  DÜZƏLİŞİN TƏSİRİ — köhnə davranışla müqayisə")
        ru_old, ru_now = legacy["field"]["ru_share"], current["field"]["ru_share"]
        print(f"    rusdilli nəticə payı     {ru_old:>6.0%} → {ru_now:>6.0%}   ({ru_now - ru_old:+.0%})")
        for lang in sorted(current["known"]["per_lang"]):
            a = legacy["known"]["per_lang"].get(lang, {}).get("mrr", 0.0)
            b = current["known"]["per_lang"][lang]["mrr"]
            print(f"    known-item MRR ({lang})     {a:>6.3f} → {b:>6.3f}   ({b - a:+.3f})")
        for lang in sorted(current["field"]["by_lang"]):
            a = legacy["field"]["by_lang"].get(lang, 0.0)
            b = current["field"]["by_lang"][lang]
            print(f"    sahə dəqiqliyi ({lang})     {a:>6.0%} → {b:>6.0%}   ({b - a:+.0%})")

    print("\n  Qeyd: sahə dəqiqliyi məqalənin BİR NEÇƏ sahəyə aid ola bilməsi")
    print("  səbəbindən 100% olmur — bu, səhv deyil, korpusun təbiətidir.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
