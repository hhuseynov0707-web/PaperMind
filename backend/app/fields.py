"""Texnologiya sahələri — arXiv kateqoriyalarının qruplaşdırılması.

Frontend-dəki sahə seçicisi bu açarlarla işləyir; axtarış və sual-cavab
seçilmiş sahənin kateqoriyaları ilə məhdudlaşdırılır.
"""

FIELDS: dict[str, list[str]] = {
    "ai": ["cs.AI", "cs.LG", "cs.CL", "cs.NE", "stat.ML"],
    "cv": ["cs.CV", "eess.IV"],
    "security": ["cs.CR"],
    "robotics": ["cs.RO", "cs.SY", "eess.SY"],
    "software": ["cs.SE", "cs.PL"],
    "data": ["cs.DB", "cs.IR", "cs.DC"],
    "networks": ["cs.NI", "cs.OS", "cs.AR"],
    "hci": ["cs.HC", "cs.CY"],
}

ALL_CATEGORIES: list[str] = sorted({c for cats in FIELDS.values() for c in cats})
