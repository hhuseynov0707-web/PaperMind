"""Sürət limitlərinin TƏK yeri.

Əvvəl rəqəmlər `config.py`-də, pəncərələr isə çağırış yerlərində bərkidilmişdi:
`limit_auth_attempt(..., 3600)` kimi. Nəticədə «giriş limiti neçədir» sualına
cavab vermək üçün üç fayla baxmaq lazım gəlirdi və pəncərəni dəyişən adam
mesajdakı «bir saat sonra» sətrini yeniləməyi unudurdu.

İndi qayda bir yerdədir: ad, hədd, pəncərə, əhatə. Mesaj isə Redis-dən
QALAN vaxtı oxuyur — sabit mətn deyil, ona görə pəncərə dəyişəndə mesaj
özü düzəlir.

## Əhatə niyə vacibdir

`login` üçün İKİ qayda var və bu, təsadüf deyil:

- `ip`      — bir ünvandan çox sayda cəhd (adi brute-force)
- `account` — çox sayda ünvandan BİR hesaba cəhd

Yalnız IP limiti qoysaq, botnet hər IP-dən bir parol sınayıb istənilən
hesabı sındıra bilər — limit heç vaxt işə düşmür. Yalnız hesab limiti
qoysaq, hücumçu qurbanın hesabını qəsdən kilidləyə bilər (DoS). İkisi
birlikdə hər iki hücumu bağlayır.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException

from .cache import _r
from .config import settings


@dataclass(frozen=True)
class Rule:
    """Bir limit qaydası.

    `window` saniyədədir. `scope` sayğacın nəyə görə ayrıldığını deyir:
    "ip", "account" (e-poçt), "user" (giriş etmiş istifadəçi) və ya
    "global" (bütün sistem üçün ümumi tavan).
    """

    limit: int
    window: int
    scope: str


# ---------------------------------------------------------------------------
# QAYDALAR
#
# Mühit dəyişəni ilə dəyişdirilə bilənlər `settings`-dən oxunur ki, serverdə
# yenidən qurmadan tənzimlənsin. Qalanları burada sabitdir.
# ---------------------------------------------------------------------------

RULES: dict[str, tuple[Rule, ...]] = {
    # Giriş: 15 dəqiqədə 5 cəhd. Həm ünvana, həm hesaba.
    "login": (
        Rule(settings.login_rate_limit, 900, "ip"),
        Rule(settings.login_rate_limit, 900, "account"),
    ),

    # Qeydiyyat: saatda 3. Bir IP-dən onlarla saxta hesab açılmasın —
    # hər hesab pulsuz kredit gətirir, yəni bu, birbaşa xərcdir.
    "signup": (Rule(settings.signup_rate_limit, 3600, "ip"),),

    # LLM sualı: IP üzrə saatlıq + bütün sistem üçün günlük tavan.
    # Günlük tavan olmasa, bir neçə IP ilə aylıq Groq büdcəsi bir gecədə yanır.
    "ask": (
        Rule(settings.ask_rate_limit, 3600, "ip"),
        Rule(settings.ask_daily_budget, 86400, "global"),
    ),

    # Axtarış ucuzdur (LLM yoxdur) — yalnız sui-istifadəyə qarşı geniş limit.
    "search": (Rule(settings.search_rate_limit, 3600, "ip"),),

    # PDF yükləmə krediti YEMİR (`CREDIT_COST[UPLOAD_PDF] = 0`), yəni kredit
    # sistemi onu heç cür məhdudlaşdırmır. Emal isə bahalıdır: 300 səhifəni
    # parçalayıb embedding çıxarmaq CPU və yaddaş tələb edir, nəticə isə
    # bazada qalır. Saatda 10 sənəd real istifadə üçün bol, avtomatlaşdırılmış
    # sui-istifadə üçün isə dardır.
    "upload": (Rule(10, 3600, "user"),),

    # Çoxməqaləli analiz — hər biri bir neçə LLM çağırışıdır.
    "analysis": (Rule(30, 3600, "user"),),
}


def _describe(seconds: int) -> str:
    """Qalan vaxtı istifadəçinin anlayacağı şəkildə yazır."""
    if seconds <= 60:
        return "bir dəqiqədən az"
    if seconds < 3600:
        return f"{seconds // 60} dəqiqə"
    hours = seconds // 3600
    return f"{hours} saat" if hours > 1 else "bir saat"


def _hit(key: str, rule: Rule) -> tuple[bool, int]:
    """Sayğacı artırır. (icazə_var, qalan_saniyə) qaytarır.

    Redis əlçatmazdırsa icazə verilir — bu, qəsdəndir: keş nasazlığı bütün
    girişi dayandırmamalıdır. Əvəzində yazma qorunması (admin açarı) Redis-dən
    ASILI DEYİL, yəni keş düşəndə də bazaya yazmaq mümkün olmur.
    """
    try:
        used = _r.incr(key)
        if used == 1:
            _r.expire(key, rule.window)
        if used <= rule.limit:
            return True, 0
        ttl = _r.ttl(key)
        return False, ttl if isinstance(ttl, int) and ttl > 0 else rule.window
    except Exception:
        return True, 0


def enforce(name: str, *, ip: str | None = None, account: str | None = None,
            user_id: int | None = None) -> None:
    """Adlandırılmış qaydanı tətbiq edir; limitə çatanda 429 atır.

    Mesaj REAL qalan vaxtı deyir, sabit mətn yox — pəncərəni dəyişəndə
    istifadəçiyə deyilən vaxt da özü düzəlir.
    """
    if not settings.public_mode:
        return                      # lokal işdə limit yoxdur

    values = {"ip": ip, "account": (account or "").strip().lower() or None,
              "user": str(user_id) if user_id else None, "global": "all"}

    for rule in RULES.get(name, ()):
        subject = values.get(rule.scope)
        if not subject:
            continue                # bu əhatə üçün dəyər yoxdursa, qayda atlanır
        ok, retry = _hit(f"rl:{name}:{rule.scope}:{subject}", rule)
        if not ok:
            raise HTTPException(
                status_code=429,
                detail=f"Çox sayda cəhd oldu. {_describe(retry)} sonra yenidən yoxla.",
                headers={"Retry-After": str(retry)},
            )
