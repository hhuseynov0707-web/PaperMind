"""RAG keyfiyyətinin ölçülməsi — §20.

Retrieval benchmark axtarışın nə tapdığını ölçür. Bu skript isə CAVABIN
sübutla əlaqəsini ölçür — §8-in tələb etdiyi şeyi:

  groundedness        — cavabdakı istinadların neçə faizi kontekstdə həqiqətən var
  citation correctness— uydurulmuş istinad olan cavabların payı
  citation coverage   — verilən sübutun neçə faizinə istinad edilib
  unsupported rate    — heç bir istinadı olmayan cavabların payı
  weak evidence rate  — sübutu zəif olan sorğuların payı
  refusal rate        — sistemin "tapılmadı" dediyi hallar

Vacib: bu ölçmə produksiya funksiyalarını (select_evidence, ask_llm,
validate_citations) BİRBAŞA çağırır — benchmark-la eyni prinsip, ölçülən
davranışla istifadəçinin gördüyü davranış ayrıla bilməz.

    docker compose exec backend python scripts/rag_eval.py --sample 20
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, "/app")

from sqlalchemy import func, select                    # noqa: E402
from app.config import settings                        # noqa: E402
from app.database import SessionLocal                  # noqa: E402
from app.models import Paper                           # noqa: E402
from app.rag.evidence import (                         # noqa: E402
    label_blocks,
    select_evidence,
    validate_citations,
)
from app.rag.llm import ask_llm                        # noqa: E402
from app.rag.retriever import retrieve                 # noqa: E402
from app.rag.translator import retrieval_inputs        # noqa: E402

QUERIES = Path(__file__).resolve().parent.parent / "eval" / "queries.json"

# Cavabın "tapılmadı" olduğunu göstərən işarələr (3 dildə)
REFUSAL = ("tapılmadı", "tapmadım", "не найдено", "не содержит", "not found",
           "does not contain", "no information", "məlumat yoxdur")


def looks_like_refusal(answer: str) -> bool:
    low = answer.lower()
    return any(marker.lower() in low for marker in REFUSAL)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=20, help="neçə sorğu (LLM çağırışı bahalıdır)")
    ap.add_argument("--top-k", type=int, default=5)
    # Groq pulsuz qatında dəqiqəlik limit var — fasilə olmadan 429 alınır
    ap.add_argument("--delay", type=float, default=3.0, help="sorğular arası fasilə (san)")
    args = ap.parse_args()

    if not settings.groq_api_key:
        print("GROQ_API_KEY yoxdur — RAG ölçməsi LLM tələb edir.")
        return 1

    spec = json.loads(QUERIES.read_text(encoding="utf-8"))
    # Determinizm: hər dəfə eyni sorğular, eyni sırada
    queries = sorted(spec["field_queries"], key=lambda x: (x["lang"], x["field"], x["q"]))
    queries = queries[:: max(1, len(queries) // args.sample)][: args.sample]

    db = SessionLocal()
    total_papers = db.scalar(select(func.count(Paper.id))) or 0

    print("PaperMind — RAG evaluation (§20)")
    print("=" * 56)
    print(f"  korpus : {total_papers} məqalə")
    print(f"  sorğu  : {len(queries)}")
    print(f"  model  : {settings.groq_model}\n")

    stats = {"grounded": [], "coverage": [], "invented": 0, "no_citation": 0,
             "weak": 0, "refusal": 0, "latency": [], "answers": []}

    for i, item in enumerate(queries, 1):
        q, lang_hint = item["q"], item["lang"]
        t0 = time.perf_counter()

        query, also, lang, _ = retrieval_inputs(q)
        blocks = retrieve(db, query, top_k=args.top_k, also=also,
                          lang=lang, mode=settings.retrieval_mode)
        blocks, ev = select_evidence(blocks, max_blocks=args.top_k)
        if not blocks:
            print(f"  [{i:>2}] {lang_hint} · sübut yoxdur · {q[:44]}")
            continue

        try:
            raw = ask_llm(q, blocks, lang=lang)
        except Exception as exc:
            msg = str(exc)
            if "429" in msg or "rate limit" in msg.lower():
                print(f"  [{i:>2}] limit — 20 san gözlənilir, təkrar")
                time.sleep(20)
                try:
                    raw = ask_llm(q, blocks, lang=lang)
                except Exception as exc2:
                    print(f"  [{i:>2}] XƏTA: {str(exc2)[:60]}")
                    continue
            else:
                print(f"  [{i:>2}] XƏTA: {msg[:60]}")
                continue

        allowed = set(label_blocks(blocks))
        answer, cite = validate_citations(raw, allowed)
        stats["latency"].append((time.perf_counter() - t0) * 1000)

        # Groundedness YALNIZ istinad yazan cavablar üzərində hesablanır.
        # İstinadsız cavab (adətən "tapılmadı") 0% kimi sayılsa, ortalama haqsız
        # aşağı düşür — halbuki o cavab yanlış istinad vermir, heç vermir.
        # İstinadsız cavabların payı ayrıca metrikdir.
        grounded = cite["valid"] / cite["cited"] if cite["cited"] else None
        if grounded is not None:
            stats["grounded"].append(grounded)
        stats["answers"].append(1)
        stats["coverage"].append(cite["coverage"])
        if cite["invented"]:
            stats["invented"] += 1
        if cite["cited"] == 0:
            stats["no_citation"] += 1
        if ev["weak"]:
            stats["weak"] += 1
        if looks_like_refusal(answer):
            stats["refusal"] += 1

        time.sleep(args.delay)
        flag = "!" if cite["invented"] else " "
        shown = "istinadsız" if grounded is None else f"grounded {grounded:.0%}"
        print(f"  [{i:>2}]{flag}{lang_hint} · {shown} · "
              f"əhatə {cite['coverage']:.0%} · {q[:40]}")

    n = len(stats["answers"])
    if not n:
        print("\nHeç bir cavab ölçülə bilmədi.")
        return 1

    print("\n" + "=" * 56)
    print("  NƏTİCƏ")
    cited_n = len(stats["grounded"])
    grounded_avg = statistics.mean(stats["grounded"]) if cited_n else 0.0
    print(f"    groundedness (istinad yazan {cited_n} cavab)      {grounded_avg:.1%}")
    print(f"    citation coverage (sübutun istifadəsi)  {statistics.mean(stats['coverage']):.1%}")
    print(f"    uydurulmuş istinadı olan cavab          {stats['invented']}/{n}")
    print(f"    heç bir istinadı olmayan cavab          {stats['no_citation']}/{n}")
    print(f"    zəif sübutlu sorğu                      {stats['weak']}/{n}")
    print(f"    «tapılmadı» cavabı                      {stats['refusal']}/{n}")
    print(f"    median gecikmə                          {statistics.median(stats['latency']):.0f} ms")
    print("\n  Qeyd: groundedness < 100% o deməkdir ki, LLM kontekstdə olmayan")
    print("  istinad yazıb — həmin istinadlar cavabdan silinir (§8).\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
