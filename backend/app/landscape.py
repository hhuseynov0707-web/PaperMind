"""Tədqiqat landşaftı (§11) və potensial boşluqlar (§13).

İkisi də eyni qaydaya tabedir: **statistika uydurulmur**. Hər rəqəm indekslənmiş
korpusdan sayılır, hər klaster real məqalələrə bağlanır.

§13-ün ən vacib bəndi dil məsələsidir. Sistem HEÇ VAXT «X haqqında tədqiqat
yoxdur» deməməlidir — bunu bilmir, yalnız öz indeksini görür. Doğru ifadə:
«indekslənmiş korpusda X haqqında məhdud sübut var». Bu fərq `GAP_PHRASING`-də
üç dildə saxlanılır ki, təsadüfən pozulmasın.
"""

from collections import Counter

from .rag.insights import INSIGHT_FIELDS

# §13: icazə verilən ifadə. Kod bu sətirləri işlədir, sərbəst mətn yazmır.
GAP_PHRASING = {
    "az": "İndekslənmiş korpusda «{topic}» üzrə məhdud sübut var ({n} məqalə).",
    "ru": "В индексированном корпусе по теме «{topic}» мало данных ({n} статей).",
    "en": "The indexed corpus contains limited evidence regarding “{topic}” ({n} papers).",
}

# Boşluq siqnalı sayılması üçün minimum təkrar. Bir məqalədə bir dəfə yazılmış
# məhdudiyyət tendensiya deyil.
MIN_SIGNAL_REPEAT = 2

# Klasterin göstərilməsi üçün minimum məqalə. Bundan azı «klaster» deyil.
MIN_CLUSTER_SIZE = 2


def build_landscape(papers: list, insights: dict[int, dict]) -> dict:
    """Verilmiş məqalə dəstindən struktur landşaft qurur (§11).

    `papers`  — models.Paper siyahısı (retrieval nəticəsi)
    `insights`— {paper_id: insight_data}; boş ola bilər

    Klasterlər iki mənbədən gəlir:
      1. `field_keys` — bütün məqalələrdə var, etibarlıdır
      2. çıxarışdakı `topics` — daha incə, amma yalnız çıxarışı olan məqalələrdə

    Hər klasterdə nümayəndə məqalələr göstərilir ki, istifadəçi rəqəmi
    yoxlaya bilsin.
    """
    if not papers:
        return {"total": 0, "clusters": [], "authors": [], "span": None, "languages": []}

    by_field: dict[str, list] = {}
    for p in papers:
        for key in (p.field_keys or []):
            by_field.setdefault(key, []).append(p)

    topics = Counter()
    methods = Counter()
    for p in papers:
        data = insights.get(p.id) or {}
        for t in (data.get("topics") or []):
            topics[t.lower()] += 1
        for m in (data.get("methods") or []):
            methods[m.lower()] += 1

    clusters = []
    for key, group in sorted(by_field.items(), key=lambda kv: -len(kv[1])):
        if len(group) < MIN_CLUSTER_SIZE:
            continue
        clusters.append({
            "key": key,
            "count": len(group),
            "share": round(len(group) / len(papers), 3),
            # Nümayəndə: ən yeni üç məqalə — rəqəmin arxasında nə durduğu görünsün
            "representative": [
                {"id": x.id, "title": x.title, "doi": x.doi, "arxiv_id": x.arxiv_id}
                for x in sorted(
                    group, key=lambda x: (x.published_at is not None, x.published_at), reverse=True
                )[:3]
            ],
        })

    author_counts = Counter()
    for p in papers:
        for a in p.authors:
            author_counts[a.name] += 1

    dates = [p.published_at for p in papers if p.published_at]
    return {
        "total": len(papers),
        "clusters": clusters,
        "topics": [{"name": t, "count": c} for t, c in topics.most_common(12)],
        "methods": [{"name": m, "count": c} for m, c in methods.most_common(12)],
        "authors": [
            {"name": n, "count": c} for n, c in author_counts.most_common(8) if c > 1
        ],
        "languages": sorted({p.language for p in papers if p.language}),
        "span": {
            "from": min(dates).date().isoformat(),
            "to": max(dates).date().isoformat(),
        } if dates else None,
        "insights_available": sum(1 for p in papers if insights.get(p.id)),
    }


def find_gaps(papers: list, insights: dict[int, dict], lang: str = "az") -> dict:
    """Potensial tədqiqat boşluqları — §13.

    Sübut mənbələri (uydurma yox, mətndən sayılan):
      - təkrarlanan MƏHDUDİYYƏTLƏR
      - təkrarlanan GƏLƏCƏK İŞ ifadələri
      - zəif təmsil olunan sahə kəsişmələri

    Nəticə həmişə «AI-GENERATED RESEARCH OPPORTUNITIES» kimi etiketlənir və
    hər maddə onu dayaqlayan məqalələrə bağlanır.
    """
    limitation_signals: list[dict] = []
    future_signals: list[dict] = []

    for p in papers:
        data = insights.get(p.id) or {}
        for key, bucket in (("limitations", limitation_signals), ("future_work", future_signals)):
            entry = data.get(key)
            if isinstance(entry, dict) and entry.get("value"):
                bucket.append({
                    "paper_id": p.id,
                    "title": p.title,
                    "text": entry["value"],
                    # Sübut tipi saxlanılır: «inferred» məhdudiyyət məqalənin
                    # yazdığı deyil, modelin nəticəsidir — istifadəçi bilməlidir
                    "evidence": entry.get("evidence", "inferred"),
                })

    # Zəif təmsil olunan sahələr: korpusda var, amma çox nazik
    field_counts = Counter()
    for p in papers:
        for key in (p.field_keys or []):
            field_counts[key] += 1
    thin = [
        {"field": k, "count": c, "note": GAP_PHRASING.get(lang, GAP_PHRASING["en"]).format(topic=k, n=c)}
        for k, c in field_counts.items()
        if c < MIN_SIGNAL_REPEAT * 2
    ]

    return {
        "label": "AI-GENERATED RESEARCH OPPORTUNITIES",
        "disclaimer": GAP_PHRASING.get(lang, GAP_PHRASING["en"]),
        "repeated_limitations": limitation_signals[:10],
        "stated_future_work": future_signals[:10],
        "thin_areas": sorted(thin, key=lambda x: x["count"])[:8],
        "evidence_base": {
            "papers_examined": len(papers),
            "papers_with_insights": sum(1 for p in papers if insights.get(p.id)),
            # Şəffaflıq: çıxarışı olmayan məqalələr siqnal verə bilməz
            "coverage": round(
                sum(1 for p in papers if insights.get(p.id)) / len(papers), 3
            ) if papers else 0.0,
        },
    }


def insight_coverage(insights: dict[int, dict]) -> dict:
    """Çıxarışların hansı sahələri nə qədər doldurduğu.

    Landşaft və boşluq analizinin nə qədər dayaqlı olduğunu göstərir: əgər
    məqalələrin yalnız 10%-də `limitations` varsa, «təkrarlanan məhdudiyyət»
    siqnalı zəifdir və bunu gizlətmək olmaz.
    """
    filled = Counter()
    for data in insights.values():
        for key in INSIGHT_FIELDS:
            if isinstance(data.get(key), dict) and data[key].get("value"):
                filled[key] += 1
    n = len(insights) or 1
    return {key: {"filled": filled[key], "share": round(filled[key] / n, 3)} for key in INSIGHT_FIELDS}
