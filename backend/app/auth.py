"""Hesab, sessiya və kredit qatı.

Üç qərar burada verilib və hər birinin səbəbi var:

1. **Parol argon2id ilə həshlənir.** OWASP-ın birinci seçimidir; yaddaş-ağır
   olduğu üçün GPU ilə kütləvi sınaq bahalaşır. Öz sxemimizi qurmuruq.

2. **Sessiya opak tokendir, JWT yox.** JWT vaxtından əvvəl ləğv edilə bilmir;
   bizdə isə çıxış, plan dəyişikliyi və hesabın bloklanması dərhal təsir
   etməlidir. Token bazada AÇIQ saxlanılmır — yalnız SHA-256 həshi.

3. **Kredit yazılışı tək SQL ifadəsidir.** «Oxu → yoxla → yaz» ardıcıllığı
   paralel sorğularda limiti aşmağa imkan verir (iki sorğu eyni qalığı görür).
   Şərt UPDATE-in özündədir, ona görə yarış mümkün deyil.
"""

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Cookie, Depends, HTTPException, Request, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models, plans
from .config import settings
from .database import get_db
from .security import _hit, client_ip

SESSION_COOKIE = "pm_session"

_ph = PasswordHasher()

# Sadə e-poçt yoxlaması. Məqsəd doğruluğu SÜBUT etmək deyil — RFC-yə tam uyğun
# regex praktiki olaraq oxunmazdır; məqsəd açıq zibili kəsməkdir.
_EMAIL = re.compile(r"^[^@\s]+@[^@\s.]+\.[^@\s]+$")


# --- Parol ------------------------------------------------------------------

def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def valid_email(email: str) -> bool:
    return bool(_EMAIL.match(email)) and len(email) <= 254


def password_problem(password: str) -> str | None:
    """Qaytarır: problem mətni, yaxud None.

    NIST tövsiyəsinə uyğun olaraq UZUNLUQ tələb olunur, «bir böyük hərf + bir
    rəqəm + bir simvol» yox: sonuncu qayda istifadəçini `Parol1!` kimi zəif,
    amma «uyğun» parollara yönəldir.
    """
    if len(password or "") < settings.min_password_length:
        return f"Parol ən azı {settings.min_password_length} simvol olmalıdır."
    if len(password) > 200:
        return "Parol çox uzundur."
    return None


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    """Uyğunsuzluq da, korlanmış həsh də «yanlış parol» sayılır.

    Geniş `except` qəsdəndir: yoxlamanın hər hansı səbəbdən alınmaması
    autentifikasiyanın UĞURSUZ olması deməkdir, xəta atıb 500 qaytarmaq yox.
    """
    try:
        _ph.verify(stored_hash, password)
        return True
    except VerifyMismatchError:
        return False
    except Exception:
        return False


# Mövcud olmayan e-poçt üçün də həsh hesablanır ki, cavab müddəti «bu e-poçt
# qeydiyyatdadır» siqnalı verməsin. Dəyər əhəmiyyətsizdir, xərci vacibdir.
_DUMMY_HASH = _ph.hash("papermind-timing-equalizer")


def waste_time_like_a_real_check() -> None:
    try:
        _ph.verify(_DUMMY_HASH, "wrong")
    except Exception:
        pass


# --- Sessiya ----------------------------------------------------------------

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user: models.User, request: Request, response: Response) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=settings.session_ttl_days)
    db.add(
        models.UserSession(
            user_id=user.id,
            token_hash=_token_hash(token),
            expires_at=expires,
            user_agent=(request.headers.get("user-agent") or "")[:300],
            ip=client_ip(request),
        )
    )
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_ttl_days * 86400,
        httponly=True,                       # JS oxuya bilmir → XSS ilə oğurlanmır
        secure=settings.session_cookie_secure,
        samesite="lax",                      # CSRF-in əsas vektorunu bağlayır
        path="/",
    )
    return token


def destroy_session(db: Session, token: str | None, response: Response) -> None:
    if token:
        db.query(models.UserSession).filter(
            models.UserSession.token_hash == _token_hash(token)
        ).delete()
        db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


def destroy_all_sessions(db: Session, user_id: int) -> int:
    n = db.query(models.UserSession).filter(models.UserSession.user_id == user_id).delete()
    db.commit()
    return n


# --- Asılılıqlar ------------------------------------------------------------

def current_user(
    db: Session = Depends(get_db),
    pm_session: str | None = Cookie(default=None),
) -> models.User | None:
    """Girişsiz də işləyir — None qaytarır. Açıq endpoint-lər bunu işlədir."""
    if not pm_session:
        return None
    row = (
        db.query(models.UserSession)
        .filter(models.UserSession.token_hash == _token_hash(pm_session))
        .first()
    )
    if row is None:
        return None
    if row.expires_at <= datetime.now(timezone.utc):
        db.delete(row)
        db.commit()
        return None
    user = db.get(models.User, row.user_id)
    if user is None or not user.is_active:
        return None
    return user


def require_user(user: models.User | None = Depends(current_user)) -> models.User:
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Bu əməliyyat üçün hesaba giriş lazımdır.",
        )
    return user


def optional_user_or_gate(user: models.User | None = Depends(current_user)) -> models.User | None:
    """Açıq baxış üçün: PUBLIC_BROWSE sönülüdürsə giriş məcburidir.

    Bu, «qapını bağla» qərarını TƏK yerdə saxlayır — fikir dəyişəndə endpoint-lər
    toxunulmur, yalnız konfiqurasiya dəyişir.
    """
    if settings.public_browse:
        return user
    if user is None:
        raise HTTPException(status_code=401, detail="Platformaya giriş üçün hesab lazımdır.")
    return user


def require_capability(action: str):
    """Endpoint üçün imkan yoxlayıcısı qaytarır.

    İmkan olmayanda 402 qaytarılır, 403 yox: «ödəniş tələb olunur» semantik
    olaraq doğrudur və frontend bunu yüksəltmə təklifindən ayıra bilir.
    """

    def _dep(user: models.User = Depends(require_user)) -> models.User:
        plan = plans.get_plan(user.plan)
        if action not in plan.capabilities:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "upgrade_required",
                    "action": action,
                    "plan": plan.key,
                    "message": "Bu imkan Pro planındadır.",
                },
            )
        return user

    return _dep


# --- Kredit -----------------------------------------------------------------

def _period() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m")


# Şərt UPDATE-in İÇİNDƏDİR: iki paralel sorğu eyni qalığı oxuyub ikisi də
# keçə bilməsin. Dövr dəyişibsə sayğac elə burada sıfırlanır — ayın əvvəlində
# cron işlətmək lazım deyil (cron işləməsə istifadəçi səssizcə bloklanardı).
_CHARGE_SQL = text(
    """
    UPDATE users
       SET credits_used = CASE WHEN credits_period = :period
                               THEN credits_used + :cost
                               ELSE :cost END,
           credits_period = :period
     WHERE id = :uid
       AND ((credits_period IS DISTINCT FROM :period AND :cost <= :limit)
            OR (credits_period = :period AND credits_used + :cost <= :limit))
    RETURNING credits_used
    """
)


def charge(db: Session, user: models.User, action: str, meta: dict | None = None) -> int:
    """Krediti yazır. Qalıq çatmırsa 402 atır.

    Qaytarır: bu dövrdə istifadə olunmuş ümumi kredit.
    """
    cost = plans.cost_of(action)
    limit = plans.get_plan(user.plan).monthly_credits

    if cost == 0:
        return user.credits_used or 0

    row = db.execute(
        _CHARGE_SQL,
        {"period": _period(), "cost": cost, "uid": user.id, "limit": limit},
    ).first()

    if row is None:
        db.rollback()
        raise HTTPException(
            status_code=402,
            detail={
                "error": "out_of_credits",
                "action": action,
                "plan": user.plan,
                "limit": limit,
                "message": "Bu ayın kreditləri bitdi.",
            },
        )

    db.add(
        models.UsageEvent(user_id=user.id, action=action, credits=cost, meta=meta or {})
    )
    db.commit()
    # ORM obyekti xam UPDATE-dən sonra köhnə dəyəri saxlayır — çağıran tərəf
    # `user.credits_used` oxusa səhv rəqəm görərdi.
    db.refresh(user)
    return int(row[0])


def credits_left(user: models.User) -> int:
    limit = plans.get_plan(user.plan).monthly_credits
    # Dövr keçibsə sayğac hələ sıfırlanmayıb (sıfırlama ilk yazılışda baş verir),
    # ona görə oxuyanda köhnə dövrün rəqəmi nəzərə alınmır.
    used = (user.credits_used or 0) if user.credits_period == _period() else 0
    return max(0, limit - used)


# --- Sürət limiti -----------------------------------------------------------

def limit_auth_attempt(request: Request, kind: str, limit: int) -> None:
    """Qeydiyyat/giriş üçün IP limiti.

    Parol sınaqlarını yavaşladır. Redis əlçatmazdırsa `_hit` icazə verir —
    bu, qəsdəndir: keş problemi bütün girişi dayandırmamalıdır.
    """
    ok, _ = _hit(f"rl:auth:{kind}:{client_ip(request)}", limit, 3600)
    if not ok:
        raise HTTPException(
            status_code=429,
            detail="Çox sayda cəhd. Bir saat sonra yenidən yoxla.",
            headers={"Retry-After": "3600"},
        )
