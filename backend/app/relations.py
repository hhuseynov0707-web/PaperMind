"""Məqalələr arası əlaqələr — §15.

§15 səkkiz əlaqə tipi sadalayır. Onlar ETİBARLILIQ baxımından bərabər deyil və
bu fərq gizlədilməməlidir:

    cites          FAKT     — OpenAlex `referenced_works`, mənbədən gəlir
    same_authors   TÖRƏMƏ   — ad kəsişməsi; «eyni soyad» ≠ «eyni adam»
    related_to     TÖRƏMƏ   — vektor oxşarlığı, ölçülə bilən
    builds_on      TÖRƏMƏ   — sitat + zaman istiqaməti
    contradicts    MÜHAKİMƏ — LLM qiymətləndirməsi (§10)
    supports       MÜHAKİMƏ
    replicates     MÜHAKİMƏ
    uses_method    MÜHAKİMƏ — çıxarışdakı metodların kəsişməsi

Ona görə hər əlaqə `confidence` və `source` ilə saxlanılır: interfeys faktı
mühakimədən ayıra bilməlidir. Hamısını eyni etibarla göstərmək sistemi
inandırıcı görünən uydurmaya çevirərdi.

**Graph DB qurulmadı** — §15 bunu açıq şəkildə istəmir və 1 600 məqaləlik
korpusda iki indeksli Postgres cədvəli bütün keçidləri millisaniyələrlə verir.
"""

RELATION_TYPES = (
    "cites",
    "builds_on",
    "extends",
    "supports",
    "contradicts",
    "replicates",
    "uses_method",
    "related_to",
    "same_authors",
)

# Mənbəyə görə etibarlılıq. Rəqəmlər ixtiyari deyil:
#   1.0 — xarici reyestrdən gələn fakt, yoxlanıla bilər
#   0.7 — bazadan hesablanır, amma şərh tələb edir (eyni müəllif ≠ davam işi)
#   0.5 — ölçülmüş oxşarlıq, mənalı əlaqəyə zəmanət vermir
#   LLM əsaslı əlaqələrdə confidence modelin öz qiymətindən gəlir (§10)
CONFIDENCE = {
    "openalex": 1.0,
    "authors": 0.7,
    "similarity": 0.5,
}

# Vektor oxşarlığında `related_to` üçün minimum hədd. Bundan aşağısı «eyni
# sahədir» deməkdir, «əlaqəlidir» yox — və hər məqaləni hər məqaləyə bağlamaq
# qrafiki mənasız edir.
RELATED_MIN_SCORE = 0.62
RELATED_MAX_PER_PAPER = 8


def normalize_openalex_refs(referenced_works) -> list[str]:
    """OpenAlex `referenced_works` siyahısını W-id-lərə çevirir.

    Sahə `["https://openalex.org/W123", ...]` şəklində gəlir.
    """
    from .sources.common import normalize_openalex_id

    if not isinstance(referenced_works, list):
        return []
    out = []
    for ref in referenced_works:
        oid = normalize_openalex_id(ref)
        if oid:
            out.append(oid)
    return out


def classify_citation_direction(from_year: int | None, to_year: int | None) -> str:
    """Sitat əlaqəsini dəqiqləşdirir: `cites` yoxsa `builds_on`.

    §15 `builds_on` tipini ayrıca sadalayır. Onu sitatdan ayırmaq üçün əlavə
    siqnal lazımdır; ən sadə və yoxlanıla bilən siqnal ZAMANDIR — sonrakı iş
    əvvəlkinə istinad edirsə, bu, «üzərində qurur» kimi oxuna bilər.

    Tarix bilinmirsə `cites` qalır: naməlum halda daha ZƏİF iddia seçilir.
    """
    if from_year and to_year and from_year > to_year:
        return "builds_on"
    return "cites"


def author_keys(names: list[str]) -> set[str]:
    """Müəllif adlarını «ad-baş-hərfi + soyad» açarına çevirir.

    ÖLÇÜLDÜ: yalnız soyadla uyğunlaşdıranda 1 596 məqalədən 5 551 `same_authors`
    əlaqəsi yarandı — məqalə başına ~3.5. Səbəb: «Wang», «Li», «Zhang» kimi
    soyadlar onlarla məqalədə təkrarlanır və hər qrup yüzlərlə cüt verir.
    Nəticədə əlaqə «eyni adam» yox, «eyni soyad» deməyə başlayır — sübutdan
    güclü iddia.

    Baş hərf əlavə edilməsi bunu kəskin azaldır: «Wei Wang» və «Yan Wang»
    artıq ayrılır.

    Məlumat çatışmazlığı SÜBUT SAYILMIR (dedup-dakı `has_conflicting_ids` ilə
    eyni prinsip): baş hərfi bilinməyən ad `?` ilə işarələnir və o, hər hansı
    baş hərflə uyğun gələ bilər.
    """
    import re as _re

    out = set()
    for name in names or []:
        parts = [p.strip(" .,'\"") for p in _re.split(r"[\s,]+", (name or "").lower())]
        parts = [p for p in parts if len(p) > 1 or (len(p) == 1 and p.isalpha())]
        if not parts:
            continue
        surname = max(parts, key=len)
        others = [p for p in parts if p is not surname]
        initial = others[0][0] if others else "?"
        out.add(f"{initial}.{surname}")
    return out


def author_overlap(a: list[str], b: list[str]) -> set[str]:
    """İki məqalənin ortaq müəllifləri.

    Baş hərfi bilinməyən tərəf üçün soyad uyğunluğu kifayətdir — yoxluq sübut
    deyil. Hər ikisində baş hərf varsa, onlar da uyğun gəlməlidir.
    """
    ka, kb = author_keys(a), author_keys(b)
    shared = set()
    for key_a in ka:
        ia, sa = key_a.split(".", 1)
        for key_b in kb:
            ib, sb = key_b.split(".", 1)
            if sa != sb:
                continue
            if ia == "?" or ib == "?" or ia == ib:
                shared.add(sa)
    return shared


def method_overlap(insight_a: dict, insight_b: dict) -> set[str]:
    """Çıxarışdakı ortaq metodlar — `uses_method` əlaqəsi üçün."""
    ma = {m.strip().lower() for m in (insight_a or {}).get("methods", []) if m.strip()}
    mb = {m.strip().lower() for m in (insight_b or {}).get("methods", []) if m.strip()}
    return ma & mb


def build_relation(from_id: int, to_id: int, relation: str, *,
                   source: str, evidence: str = "", confidence: float | None = None) -> dict | None:
    """Bir əlaqə qeydi qurur. Etibarsız girişdə None.

    Öz-özünə əlaqə (from == to) qadağandır — belə sətir qrafikdə mənasızdır və
    keçid sorğularında sonsuz dövrə yaradır.
    """
    if not from_id or not to_id or from_id == to_id:
        return None
    if relation not in RELATION_TYPES:
        return None
    return {
        "from_paper_id": from_id,
        "to_paper_id": to_id,
        "relation": relation,
        "confidence": confidence if confidence is not None else CONFIDENCE.get(source, 0.5),
        "evidence": evidence[:500],
        "source": source,
    }


def summarize_relations(rows: list[dict]) -> dict:
    """Əlaqələri tipə görə qruplaşdırır və etibarlılığa görə ayırır.

    İnterfeys FAKTI MÜHAKİMƏDƏN ayırmalıdır — ona görə xülasə də ayırır.
    """
    by_type: dict[str, int] = {}
    facts = judgements = 0
    for r in rows:
        by_type[r["relation"]] = by_type.get(r["relation"], 0) + 1
        if (r.get("confidence") or 0) >= 0.9:
            facts += 1
        else:
            judgements += 1
    return {
        "total": len(rows),
        "by_type": dict(sorted(by_type.items(), key=lambda kv: -kv[1])),
        "verified": facts,       # xarici reyestrdən, yoxlanıla bilən
        "derived": judgements,   # hesablanmış və ya mühakimə
    }
