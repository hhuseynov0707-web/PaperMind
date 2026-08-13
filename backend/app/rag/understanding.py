"""Sorğu anlama — §6.

Auditdə W6: sorğudan yalnız DİL çıxarılırdı. §6 isə niyyət, entity, müəllif,
tarix məhdudiyyəti və fənn tələb edir.

**LLM işlədilmir.** Səbəb ölçmədən gəlir: niyyət aşkarlaması hər axtarışda
işləyəcək, `/api/search` isə onsuz da az/ru sorğular üçün Groq tərcüməsi
çağırır (audit S3 — qlobal büdcə ona görə əlavə olundu). Bura ikinci LLM
çağırışı qoysaq, axtarış gecikməsi ~40 ms-dən saniyələrə qalxar və xərc ikiqat
olar. Niyyət isə sabit ifadə nümunələri ilə etibarlı tapılır.

Nəticə `QueryPlan`-dır: nə axtarılır, hansı məhdudiyyətlərlə və istifadəçinin
əslində NƏ İSTƏDİYİ. İnterfeys buna görə uyğun imkanı təklif edir — §19-un
tələbi budur: qabaqcıl funksiyalar görünən olsun, amma əsas axın sadə qalsın.
"""

import re
from dataclasses import asdict, dataclass, field
from datetime import date


# Azərbaycan diakritikası ASCII-yə qatlanır. Səbəb real istifadədən gəlir:
# istifadəçilər «fərq» yerinə «ferq», «mövzu» yerinə «movzu» yazır. Nümunələri
# diakritika ilə yazsaq, sorğuların çoxu tanınmazdı — layihədə eyni problem
# `translator._AZ_ASCII_HINTS`-də də həll olunub.
#
# Nümunələr AŞAĞIDA qatlanmış formada yazılır ki, hər iki yazılış eyni
# nümunəyə düşsün.
_FOLD = str.maketrans({
    "ə": "e", "Ə": "e", "ğ": "g", "Ğ": "g", "ı": "i", "İ": "i",
    "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u",
    "ç": "c", "Ç": "c",
})


def fold(text: str) -> str:
    """Diakritikanı ASCII-yə çevirir və kiçik hərfə salır (yalnız uyğunlaşdırma üçün)."""
    return (text or "").translate(_FOLD).lower()


# §6-nın tələb etdiyi niyyətlər
INTENTS = (
    "SEARCH",            # defolt: uyğun məqalələri tap
    "COMPARE",           # iki və daha çox işi qarşılaşdır
    "EXPLAIN",           # anlayışı izah et
    "TREND",             # zamanla necə dəyişib
    "EMERGING_TOPIC",    # nə yeni yaranır
    "CONTRADICTION",     # harada ziddiyyət var
    "RESEARCH_GAP",      # nə az öyrənilib
    "CROSS_DISCIPLINARY",# sahələr necə bağlıdır
)

# Niyyət nümunələri — üç dildə. Sıra VACİBDİR: yuxarıdakı daha spesifikdir.
# Məsələn «fərq» sözü həm COMPARE, həm CONTRADICTION-da olur; ziddiyyət
# nümunələri əvvəl yoxlanılır, çünki onlar daha dar mənalıdır.
_PATTERNS: list[tuple[str, str]] = [
    ("CONTRADICTION", r"ziddiyy|tezad|tekzib|eks netice|razilasmir"),
    ("CONTRADICTION", r"противореч|расхожден|опроверг|не согласуют"),
    ("CONTRADICTION", r"contradict|conflicting|disagree|inconsisten|refut"),

    ("RESEARCH_GAP", r"bosluq|az oyrenil|tedqiq olunmay|arasdirilmam|ne catismir"),
    ("RESEARCH_GAP", r"пробел|недостаточно изучен|малоизучен|не исследован"),
    ("RESEARCH_GAP", r"research gap|underexplored|understudied|open question|what is missing"),

    ("EMERGING_TOPIC", r"yeni yaran|yeni istiqamet|yeni movzu|son zamanlar (ne|hansi)"),
    ("EMERGING_TOPIC", r"новое направлени|зарождающ|новые темы"),
    ("EMERGING_TOPIC", r"emerging|newly appearing|what is new in|rising topic"),

    # «X ilə Y arasında» tək başına kifayət deyil — o, çox vaxt MÜQAYİSƏ
    # sorğusudur («transformer ilə RNN arasındakı fərq»). Fənlərarası sorğu
    # əlaqə/tətbiq sözü tələb edir.
    ("CROSS_DISCIPLINARY", r"fenlerarasi|sahelerarasi|hansi saheler|arasinda(ki)? (elaqe|bag)"),
    ("CROSS_DISCIPLINARY", r"междисциплинар|на стыке|связь между областями"),
    ("CROSS_DISCIPLINARY", r"cross[- ]disciplin|interdisciplin|how is .+ used in|bridge between"),

    ("TREND", r"trend|dinamika|zamanla|iller uzre|nece deyisib|artim"),
    ("TREND", r"тренд|динамик|со временем|по годам|как измени"),
    ("TREND", r"trend|over time|by year|how has .+ changed|growth of"),

    ("COMPARE", r"muqayise|qarsilasdir|ferq|hansi daha"),
    ("COMPARE", r"сравн|отлич|разниц|чем отличает"),
    ("COMPARE", r"compare|comparison|versus|\bvs\b|difference between"),

    ("EXPLAIN", r"nedir|ne demekdir|izah et|nece isleyir|ne ucun"),
    ("EXPLAIN", r"что такое|объясни|как работает|почему"),
    ("EXPLAIN", r"what is|what are|explain|how does .+ work|why does"),
]

_COMPILED = [(intent, re.compile(p, re.IGNORECASE)) for intent, p in _PATTERNS]

# Müəllif: yalnız AÇIQ prefikslə. Sərbəst ad tanıma (NER) işlədilmir, çünki
# «Monte Carlo», «Markov», «Gauss» kimi metod adları müəllif kimi tutulardı və
# filtr nəticəni boşaldardı.
#
# İki forma dəstəklənir və bu, QƏSDƏN dardır:
#   author:LeCun          → tək söz (soyad)
#   author:"Yann LeCun"   → dırnaqda çoxsözlü ad
#
# Dırnaqsız çoxsözlü forma qəbul edilmir: `author:LeCun attention mechanism`
# sorğusunda adın harada bitdiyini bilmək mümkün deyil. İlk versiya `[^\n,;]+`
# işlədirdi və bütün sorğunu ad kimi udurdu — nəticədə həm filtr yanlış olurdu,
# həm də axtarış mətni boşalırdı.
_AUTHOR = re.compile(
    r"""(?:author|müəllif|muellif|автор)\s*[:=]\s*
        (?:"([^"\n]{2,60})"        # dırnaqda: çoxsözlü ad
         |([^\s,;"]{2,40}))        # dırnaqsız: TƏK söz""",
    re.IGNORECASE | re.VERBOSE,
)

# Tarix: dörd rəqəmli il, il aralığı və nisbi ifadələr
_YEAR = re.compile(r"\b(19[89]\d|20[0-4]\d)\b")
_YEAR_RANGE = re.compile(r"\b(19[89]\d|20[0-4]\d)\s*[-–—]\s*(19[89]\d|20[0-4]\d)\b")
_RECENT = re.compile(
    r"(?:son|последн(?:ие|их)|last|past)\s+(\d{1,2})\s*(?:il|year|лет|года|год)", re.IGNORECASE
)
_SINCE = re.compile(r"(?:since|starting|başlayaraq|с)\s+(19[89]\d|20[0-4]\d)", re.IGNORECASE)


@dataclass
class QueryPlan:
    """Sorğunun anlaşılmış forması."""

    text: str
    intent: str = "SEARCH"
    # Bir sorğu birdən çox niyyətə uyğun gələ bilər — §6: «Do not force every
    # query into a single discipline» məntiqi niyyətə də aiddir.
    intents: list[str] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    year_from: int | None = None
    year_to: int | None = None
    # Sorğunun məhdudiyyətlərdən təmizlənmiş hissəsi — retrieval buna baxır
    core: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def detect_intents(text: str) -> list[str]:
    """Uyğun gələn bütün niyyətlər, spesifikdən ümumiyə doğru."""
    folded = fold(text)
    found: list[str] = []
    for intent, pattern in _COMPILED:
        if intent in found:
            continue
        if pattern.search(folded):
            found.append(intent)
    return found


def extract_authors(text: str) -> list[str]:
    """`author:` prefiksli müəllif adları. Boş siyahı = filtr yoxdur."""
    out = []
    for quoted, bare in _AUTHOR.findall(text or ""):
        name = (quoted or bare).strip(" .'\"")
        if name:
            out.append(name)
    return out


def extract_years(text: str, today: date | None = None) -> tuple[int | None, int | None]:
    """(year_from, year_to). Tapılmasa (None, None).

    Nisbi ifadə («son 3 il») cari ildən hesablanır; `today` test üçün verilir.
    """
    text = text or ""
    now = (today or date.today()).year

    m = _YEAR_RANGE.search(text)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return (min(a, b), max(a, b))

    m = _RECENT.search(text)
    if m:
        span = max(1, min(int(m.group(1)), 50))
        return (now - span + 1, now)

    m = _SINCE.search(text)
    if m:
        return (int(m.group(1)), now)

    years = [int(y) for y in _YEAR.findall(text)]
    if years:
        return (min(years), max(years))
    return (None, None)


def strip_constraints(text: str) -> str:
    """Məhdudiyyət ifadələrini sorğudan çıxarır.

    `author:Smith attention mechanism` sorğusunda `author:Smith` retrieval üçün
    səs-küydür — embedding onu mövzu kimi oxuyur və nəticəni pisləşdirir.
    Filtr kimi işlədilir, mətndən isə silinir.
    """
    cleaned = _AUTHOR.sub(" ", text or "")
    cleaned = _RECENT.sub(" ", cleaned)
    cleaned = _SINCE.sub(" ", cleaned)
    cleaned = _YEAR_RANGE.sub(" ", cleaned)
    return " ".join(cleaned.split())


def understand(text: str, today: date | None = None) -> QueryPlan:
    """Sorğunu tam anlaşılmış plana çevirir."""
    intents = detect_intents(text)
    year_from, year_to = extract_years(text, today)
    core = strip_constraints(text)
    return QueryPlan(
        text=text,
        intent=intents[0] if intents else "SEARCH",
        intents=intents,
        authors=extract_authors(text),
        year_from=year_from,
        year_to=year_to,
        # Məhdudiyyətlər çıxarıldıqdan sonra heç nə qalmasa, orijinala qayıdırıq —
        # boş sorğu ilə axtarış mənasızdır
        core=core or (text or "").strip(),
    )


# Niyyət → onu qarşılayan imkan. İnterfeys istifadəçini bura yönləndirir;
# §19: qabaqcıl funksiyalar görünən olsun, əsas axın sadə qalsın.
INTENT_ROUTE = {
    "COMPARE": "/api/compare",
    "CONTRADICTION": "/api/conflicts",
    "TREND": "/api/analytics/trend-classes",
    "EMERGING_TOPIC": "/api/analytics/trend-classes",
    "RESEARCH_GAP": "/api/gaps",
    "CROSS_DISCIPLINARY": "/api/cross-disciplinary",
    "EXPLAIN": "/api/ask",
    "SEARCH": "/api/search",
}
