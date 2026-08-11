"""Elm sahələri taksonomiyası.

İki səviyyə: qrup (təbiət elmləri, formal elmlər, ...) və sahə (fizika, riyaziyyat...).
`FIELDS` sahəni arXiv kateqoriyalarına bağlayır; arXiv-də qarşılığı olmayan
sahələr (tibb, psixologiya) boş siyahı ilə qalır və yalnız mətn sorğusu ilə
yığılır — mənbə strategiyası `sources/__init__.py`-dədir.

Yeni sahə əlavə etmək: bura bir sətir, `FIELD_TERMS`-ə axtarış terminləri,
`FIELD_TERMS_RU`-ya rusca qarşılıqları. Retrieval və filtr kodu dəyişmir.
"""

# Qrup -> həmin qrupa aid sahələr. İnterfeysdə iyerarxik seçici üçün.
GROUPS: dict[str, list[str]] = {
    "tech": ["ai", "cv", "security", "robotics", "software", "data", "networks", "hci"],
    "natural": ["physics", "astronomy", "chemistry", "biology", "earth"],
    "formal": ["math", "statistics"],
    "health": ["medicine", "neuroscience"],
    "social": ["economics", "psychology"],
}

FIELDS: dict[str, list[str]] = {
    # ---------------- Texnologiya və mühəndislik ----------------
    "ai": ["cs.AI", "cs.LG", "cs.CL", "cs.NE", "stat.ML"],
    "cv": ["cs.CV", "eess.IV"],
    "security": ["cs.CR"],
    "robotics": ["cs.RO", "cs.SY", "eess.SY"],
    "software": ["cs.SE", "cs.PL"],
    "data": ["cs.DB", "cs.IR", "cs.DC"],
    "networks": ["cs.NI", "cs.OS", "cs.AR"],
    "hci": ["cs.HC", "cs.CY"],

    # ---------------- Təbiət elmləri ----------------
    "physics": [
        "physics.gen-ph", "physics.optics", "physics.flu-dyn", "physics.plasm-ph",
        "cond-mat.mes-hall", "cond-mat.mtrl-sci", "cond-mat.stat-mech", "cond-mat.supr-con",
        "quant-ph", "gr-qc", "hep-th", "hep-ph", "hep-ex", "nucl-th", "nucl-ex",
    ],
    "astronomy": [
        "astro-ph.GA", "astro-ph.CO", "astro-ph.EP", "astro-ph.HE",
        "astro-ph.IM", "astro-ph.SR",
    ],
    "chemistry": ["physics.chem-ph", "cond-mat.soft"],
    "biology": [
        "q-bio.BM", "q-bio.CB", "q-bio.GN", "q-bio.MN",
        "q-bio.PE", "q-bio.QM", "q-bio.TO", "q-bio.SC",
    ],
    "earth": ["physics.ao-ph", "physics.geo-ph", "physics.space-ph"],

    # ---------------- Formal elmlər ----------------
    "math": [
        "math.NA", "math.OC", "math.PR", "math.ST", "math.CO",
        "math.AP", "math.DS", "math.LO", "math.AT", "math.GR",
    ],
    "statistics": ["stat.ME", "stat.TH", "stat.AP", "stat.CO"],

    # ---------------- Tibb və sağlamlıq ----------------
    # arXiv bu sahələri praktiki olaraq əhatə etmir — Crossref/DOAJ/OpenAlex
    # mətn sorğuları ilə yığılır. (Europe PMC konnektoru növbəti addımdır.)
    "medicine": [],
    "neuroscience": ["q-bio.NC"],

    # ---------------- Sosial elmlər ----------------
    "economics": ["econ.EM", "econ.GN", "econ.TH", "q-fin.GN", "q-fin.PM", "q-fin.ST"],
    "psychology": [],
}

ALL_CATEGORIES: list[str] = sorted({c for cats in FIELDS.values() for c in cats})

# Sahə -> aid olduğu qrup (tərs xəritə, interfeys və analitika üçün)
FIELD_GROUP: dict[str, str] = {
    field: group for group, fields in GROUPS.items() for field in fields
}
