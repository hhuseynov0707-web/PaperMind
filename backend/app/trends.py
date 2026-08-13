"""Trend təsnifatı — §12.

Sistem indiyə qədər həftəlik SAYLARI göstərirdi; §12 isə təsnifat tələb edir:
EMERGING / GROWING / STABLE / DECLINING / INSUFFICIENT_DATA — və hər təsnifatın
SƏBƏBİNİ.

Burada LLM işlədilmir. Səbəb sadədir: bu, arifmetikadır və arifmetikanı modelə
tapşırmaq həm bahalıdır, həm də təkrarlanmır. Funksiya safdır, ona görə test
olunur və nəticə deterministikdir.

Ən vacib qərar — INSUFFICIENT_DATA sinfi. §13 açıq deyir ki, «X haqqında
tədqiqat yoxdur» deməyə haqqımız yoxdur; eyni məntiqlə, 3 məqaləlik seriyada
«artım var» demək də uydurmadır. Kiçik saylarda faiz dəyişməsi mənasızdır:
1 → 2 məqalə +100%-dir, amma bu, trend deyil, təsadüfdür.
"""

import statistics

# Təsnifat üçün minimum tələblər. Bunlardan aşağısında rəqəm hesablanır, amma
# TƏSNİFAT verilmir — «bilmirik» demək yanlış təsnifatdan yaxşıdır.
MIN_WEEKS = 6           # ən azı bu qədər həftəlik nöqtə
MIN_TOTAL = 12          # ən azı bu qədər məqalə

# Nisbi dəyişmə həddləri (son yarı vs əvvəlki yarı)
GROWTH_THRESHOLD = 0.25     # +25% və yuxarı → artım
DECLINE_THRESHOLD = -0.25   # -25% və aşağı → azalma

# EMERGING: mövzu əvvəllər demək olar yox idi, indi görünür.
EMERGING_BASE_MAX = 3       # birinci yarıda bu qədər və ya az məqalə
EMERGING_RECENT_MIN = 6     # ikinci yarıda ən azı bu qədər

CLASSES = ("EMERGING", "GROWING", "STABLE", "DECLINING", "INSUFFICIENT_DATA")


def _split(counts: list[int]) -> tuple[list[int], list[int]]:
    """Seriyanı iki bərabər yarıya bölür (tək sayda olsa orta nöqtə atılır).

    Orta nöqtənin atılması vacibdir: onu hər iki yarıya qatsaq, dəyişmə
    süni şəkildə yumşalır.
    """
    half = len(counts) // 2
    if len(counts) % 2:
        return counts[:half], counts[half + 1:]
    return counts[:half], counts[half:]


def classify_trend(counts: list[int], label: str = "") -> dict:
    """Həftəlik sayları təsnif edir və səbəbini izah edir.

    `counts` zaman sırası ilə (köhnədən yeniyə) verilməlidir.
    """
    counts = [int(c) for c in (counts or [])]
    total = sum(counts)
    weeks = len(counts)

    if weeks < MIN_WEEKS or total < MIN_TOTAL:
        return {
            "label": label,
            "classification": "INSUFFICIENT_DATA",
            "reason": (
                f"Təsnifat üçün ən azı {MIN_WEEKS} həftə və {MIN_TOTAL} məqalə lazımdır; "
                f"indeksdə {weeks} həftə və {total} məqalə var."
            ),
            "total": total,
            "weeks": weeks,
            "change": None,
            "recent": sum(counts[len(counts) // 2:]) if counts else 0,
            "earlier": sum(counts[: len(counts) // 2]) if counts else 0,
        }

    earlier_series, recent_series = _split(counts)
    earlier, recent = sum(earlier_series), sum(recent_series)

    # Sıfır bazada faiz hesablamaq mümkün deyil — EMERGING məhz bu haldır
    change = (recent - earlier) / earlier if earlier else None

    if earlier <= EMERGING_BASE_MAX and recent >= EMERGING_RECENT_MIN:
        classification = "EMERGING"
        reason = (
            f"Əvvəlki yarıda cəmi {earlier} məqalə var idi, son yarıda {recent} oldu — "
            "mövzu indeksdə praktiki olaraq yeni görünür."
        )
    elif change is not None and change >= GROWTH_THRESHOLD:
        classification = "GROWING"
        reason = (
            f"Son yarı {recent} məqalə, əvvəlki yarı {earlier} — "
            f"{change:+.0%} dəyişmə, artım həddindən ({GROWTH_THRESHOLD:+.0%}) yuxarı."
        )
    elif change is not None and change <= DECLINE_THRESHOLD:
        classification = "DECLINING"
        reason = (
            f"Son yarı {recent} məqalə, əvvəlki yarı {earlier} — "
            f"{change:+.0%} dəyişmə, azalma həddindən ({DECLINE_THRESHOLD:+.0%}) aşağı."
        )
    else:
        classification = "STABLE"
        pct = f"{change:+.0%}" if change is not None else "hesablana bilmir"
        reason = (
            f"Son yarı {recent}, əvvəlki yarı {earlier} məqalə — dəyişmə {pct}, "
            f"yəni ±{GROWTH_THRESHOLD:.0%} səs-küy zolağının içindədir."
        )

    return {
        "label": label,
        "classification": classification,
        "reason": reason,
        "total": total,
        "weeks": weeks,
        "change": round(change, 4) if change is not None else None,
        "recent": recent,
        "earlier": earlier,
        "weekly_mean": round(statistics.mean(counts), 2),
    }


def classify_series(series: dict[str, list[int]]) -> list[dict]:
    """Bir neçə mövzunu təsnif edir və ən diqqətəlayiqləri önə çıxarır.

    Sıralama: EMERGING → GROWING → DECLINING → STABLE → INSUFFICIENT_DATA.
    Səbəb: istifadəçi üçün dəyər dəyişmədədir, sabit mövzuda deyil.
    """
    order = {"EMERGING": 0, "GROWING": 1, "DECLINING": 2, "STABLE": 3, "INSUFFICIENT_DATA": 4}
    results = [classify_trend(counts, label) for label, counts in series.items()]
    return sorted(
        results,
        key=lambda r: (order[r["classification"]], -(r["change"] or 0), -r["total"]),
    )
