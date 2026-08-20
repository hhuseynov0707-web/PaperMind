"""Plan, imkan və kredit matrisi — hamısı BİR faylda.

Niyə bir yerdə: gating endpoint-lərə səpələnsə, yeni endpoint yazanda kimsə
yoxlamanı unudur və pulsuz istifadəçi bahalı yola düşür. Burada endpoint
yalnız iki şey çağırır — `require_capability()` və `charge()` — öz şərtini
yazmır.

Kredit dəyərləri əməliyyatın REAL xərcinə görə seçilib, təsadüfi deyil:
sual bir LLM çağırışıdır, müqayisə isə 2-5 məqaləni oxuyub uzun kontekstlə
sintez edir. Ölçmə `usage_events` cədvəlindən gəlir — dəyərlər dəyişdirilməli
olsa, təxminlə yox, dəftərlə dəyişdirilir.
"""

from dataclasses import dataclass, field

from .config import settings

FREE = "free"
PRO = "pro"


# --- İmkanlar ---------------------------------------------------------------
# Ad = endpoint-in tələb etdiyi hüquq. Kredit AYRI ölçüdür: imkan «ümumiyyətlə
# icazəlidirmi», kredit isə «bu ay nə qədər qalıb».

ASK = "ask"                     # sübutlu sual-cavab
SAVE = "save"                   # kitabxanaya əlavə
INSIGHTS = "insights"           # məqalə çıxarışı (§7)
COMPARE = "compare"             # çoxməqaləli müqayisə (§9)
CONFLICTS = "conflicts"         # ziddiyyət analizi (§10)
GAPS = "gaps"                   # tədqiqat boşluqları (§11)
UPLOAD_PDF = "upload_pdf"       # şəxsi sənəd — Pro
ASK_LIBRARY = "ask_library"     # öz kitabxanası üzrə sintez — Pro


@dataclass(frozen=True)
class Plan:
    key: str
    label: str
    monthly_credits: int
    library_limit: int
    capabilities: frozenset[str] = field(default_factory=frozenset)


def _free() -> Plan:
    return Plan(
        key=FREE,
        label="Pulsuz",
        monthly_credits=settings.free_monthly_credits,
        library_limit=settings.free_library_limit,
        # Pulsuz qat DƏYƏRİ göstərməlidir, yoxsa qeydiyyatın mənası olmur:
        # sual, saxlama və çıxarış açıqdır — sadəcə kreditlə məhduddur.
        capabilities=frozenset({ASK, SAVE, INSIGHTS, COMPARE}),
    )


def _pro() -> Plan:
    return Plan(
        key=PRO,
        label="Pro",
        monthly_credits=settings.pro_monthly_credits,
        library_limit=settings.pro_library_limit,
        capabilities=frozenset(
            {ASK, SAVE, INSIGHTS, COMPARE, CONFLICTS, GAPS, UPLOAD_PDF, ASK_LIBRARY}
        ),
    )


def get_plan(key: str | None) -> Plan:
    """Naməlum plan adı pulsuza düşür — heç vaxt yuxarıya yox.

    Bu, təhlükəsizlik seçimidir: baza korlanarsa və ya webhook zibil yazarsa,
    nəticə istifadəçinin pulsuz qalmasıdır, pulsuz istifadəçinin Pro olması yox.
    """
    return _pro() if key == PRO else _free()


# --- Kredit dəyərləri -------------------------------------------------------
# 0 = pulsuz əməliyyat (LLM çağırışı yoxdur və ya keşdən gəlir).

CREDIT_COST: dict[str, int] = {
    ASK: 1,
    INSIGHTS: 2,
    COMPARE: 5,
    CONFLICTS: 5,
    GAPS: 8,
    ASK_LIBRARY: 8,
    SAVE: 0,
    UPLOAD_PDF: 0,      # emal xərci fayl ölçüsünə görə ayrıca hesablanacaq
}


def cost_of(action: str) -> int:
    return CREDIT_COST.get(action, 1)


# --- İnterfeys üçün təsvir --------------------------------------------------
# Qiymət BURADA saxlanılmır. Qiymət provayderdədir (Paddle) və orada dəyişəndə
# kodda köhnə rəqəmin qalması istifadəçini aldatmaq deməkdir.

PLAN_FEATURES: dict[str, dict[str, list[str]]] = {
    FREE: {
        "az": [
            "Bütün korpusda semantik axtarış",
            f"Ayda {settings.free_monthly_credits} tədqiqat krediti",
            f"Kitabxanada {settings.free_library_limit} məqalə",
            "Sübutlu cavablar və istinad yoxlaması",
            "Məqalə çıxarışı və müqayisə",
        ],
        "en": [
            "Semantic search across the whole corpus",
            f"{settings.free_monthly_credits} research credits per month",
            f"{settings.free_library_limit} papers in your library",
            "Evidence-grounded answers with citation validation",
            "Paper insights and comparison",
        ],
        "ru": [
            "Семантический поиск по всему корпусу",
            f"{settings.free_monthly_credits} исследовательских кредитов в месяц",
            f"{settings.free_library_limit} статей в библиотеке",
            "Ответы с проверкой ссылок",
            "Разбор и сравнение статей",
        ],
    },
    PRO: {
        "az": [
            f"Ayda {settings.pro_monthly_credits} tədqiqat krediti",
            f"Kitabxanada {settings.pro_library_limit} məqalə",
            "Ziddiyyət analizi və tədqiqat boşluqları",
            "Öz PDF sənədlərini yüklə və onlar haqqında sual ver",
            "Tezliklə: bütün kitabxanan üzrə sintez",
        ],
        "en": [
            f"{settings.pro_monthly_credits} research credits per month",
            f"{settings.pro_library_limit} papers in your library",
            "Contradiction analysis and research gaps",
            "Upload your own PDFs and ask questions about them",
            "Coming soon: synthesis across your entire library",
        ],
        "ru": [
            f"{settings.pro_monthly_credits} кредитов в месяц",
            f"{settings.pro_library_limit} статей в библиотеке",
            "Анализ противоречий и исследовательских пробелов",
            "Загрузка собственных PDF и вопросы по ним",
            "Скоро: синтез по всей библиотеке",
        ],
    },
}

# Hələ qurulmayan imkanlar. `capabilities` içində QALIRLAR ki, endpoint
# yazılanda gating hazır olsun — amma satış mətnində «tezliklə» kimi
# işarələnirlər. Endpoint işə düşəndə ad buradan çıxarılır və eyni anda
# PLAN_FEATURES-dəki «tezliklə» prefiksi silinir.
# ASK_LIBRARY hələ qurulmayıb — router-i yoxdur. UPLOAD_PDF isə 2026-08-19-da
# canlıya çıxdı, ona görə siyahıdan götürüldü.
#
# QEYD: `is_available()` heç yerdə çağırılmır. Yəni bu çoxluq HEÇ NƏYİ
# bağlamır — sadəcə satış mətnini idarə edir. Gerçək bağlama `capabilities`
# ilə olur (bax `_free()` / `_pro()`).
COMING_SOON: frozenset[str] = frozenset({ASK_LIBRARY})


def is_available(action: str) -> bool:
    return action not in COMING_SOON
