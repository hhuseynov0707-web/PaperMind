"""Qeydiyyat, giriş, çıxış, hesab məlumatı və hesabın silinməsi."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from .. import auth, limits, models, payments, plans
from ..config import settings
from ..database import get_db
from ..schemas import (
    DeleteAccountRequest,
    LoginRequest,
    PlanOut,
    RegisterRequest,
    UserOut,
)
from ..security import require_admin_key

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_out(db: Session, user: models.User) -> UserOut:
    plan = plans.get_plan(user.plan)
    saved = (
        db.query(models.SavedPaper).filter(models.SavedPaper.user_id == user.id).count()
    )
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        plan=plan.key,
        plan_label=plan.label,
        credits_left=auth.credits_left(user),
        credits_total=plan.monthly_credits,
        library_used=saved,
        library_limit=plan.library_limit,
        capabilities=sorted(plan.capabilities),
        subscription_status=user.subscription_status,
        plan_expires_at=user.plan_expires_at,
        created_at=user.created_at,
        deletion_requested_at=user.deletion_requested_at,
        deletion_effective_at=_effective_at(user),
    )


def _effective_at(user: models.User) -> datetime | None:
    """Silinmənin faktiki tarixi. İnterfeys «X tarixində silinəcək» yazır —
    möhlət günlərini frontend-də ikinci dəfə hesablamaq iki həqiqət mənbəyi
    yaradardı və möhlət dəyişəndə interfeys yalan danışardı."""
    if user.deletion_requested_at is None:
        return None
    return user.deletion_requested_at + timedelta(days=settings.account_deletion_grace_days)


@router.post("/register", response_model=UserOut, status_code=201)
def register(
    req: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    email = auth.normalize_email(req.email)
    limits.enforce("signup", ip=auth.client_ip(request), account=email)

    if not auth.valid_email(email):
        raise HTTPException(status_code=422, detail="E-poçt ünvanı düzgün deyil.")

    problem = auth.password_problem(req.password)
    if problem:
        raise HTTPException(status_code=422, detail=problem)

    if db.query(models.User).filter(models.User.email == email).first():
        # Qəsdən 409 və AÇIQ mesaj: qeydiyyat formasında e-poçtun tutulduğunu
        # gizlətmək mümkün deyil (istifadəçi onsuz da cəhd edib öyrənir), amma
        # GİRİŞ endpoint-i heç nə açıqlamır — sadalama riski oradadır.
        raise HTTPException(status_code=409, detail="Bu e-poçt artıq qeydiyyatdadır.")

    user = models.User(
        email=email,
        password_hash=auth.hash_password(req.password),
        display_name=(req.display_name or "").strip() or None,
        plan=plans.FREE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    auth.create_session(db, user, request, response)
    return _user_out(db, user)


@router.post("/login", response_model=UserOut)
def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    email = auth.normalize_email(req.email)
    # Həm ünvana, həm HESABA. Yalnız IP limiti olsaydı, botnet hər ünvandan
    # bir parol sınayıb limitə heç vaxt dəyməzdi.
    limits.enforce("login", ip=auth.client_ip(request), account=email)

    user = db.query(models.User).filter(models.User.email == email).first()

    # Hesab yoxdursa da həsh hesablanır: cavab müddəti «bu e-poçt var» siqnalı
    # verməsin. Mesaj hər iki halda eynidir.
    if user is None:
        auth.waste_time_like_a_real_check()
        raise HTTPException(status_code=401, detail="E-poçt və ya parol yanlışdır.")

    if not auth.verify_password(user.password_hash, req.password):
        raise HTTPException(status_code=401, detail="E-poçt və ya parol yanlışdır.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Hesab dayandırılıb.")

    auth.create_session(db, user, request, response)
    return _user_out(db, user)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    pm_session: str | None = Cookie(default=None),
):
    auth.destroy_session(db, pm_session, response)


@router.get("/me", response_model=UserOut)
def me(db: Session = Depends(get_db), user: models.User = Depends(auth.require_user)):
    return _user_out(db, user)


@router.get("/plans", response_model=list[PlanOut])
def list_plans(lang: str = "az"):
    """Qiymət BURADA yoxdur — o, ödəniş provayderindədir.

    Səbəb: qiyməti iki yerdə saxlamaq onların ayrılmasına gətirir və istifadəçi
    saytda bir rəqəm, checkout-da başqasını görür.
    """
    out = []
    for plan in (plans.get_plan(plans.FREE), plans.get_plan(plans.PRO)):
        features = plans.PLAN_FEATURES.get(plan.key, {})
        out.append(
            PlanOut(
                key=plan.key,
                label=plan.label,
                monthly_credits=plan.monthly_credits,
                library_limit=plan.library_limit,
                price_label=plan.price_label,
                capabilities=sorted(plan.capabilities),
                features=features.get(lang, features.get("az", [])),
            )
        )
    return out


# ---------------------------------------------------------------- silmə (§17)

@router.post("/account/delete", response_model=UserOut)
def request_deletion(
    req: DeleteAccountRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_user),
):
    """Hesabın silinməsini tələb edir — DƏRHAL silmir.

    Sətir möhlət bitəndən sonra `purge` ilə silinir. Möhlət var, çünki bu
    əməliyyat geri qaytarıla bilməz və təsadüfi klik bütün kitabxananı,
    sənədləri və tarixçəni aparır.
    """
    if not auth.verify_password(user.password_hash, req.password):
        auth.waste_time_like_a_real_check()
        raise HTTPException(status_code=401, detail="Parol yanlışdır.")

    # Aktiv abunəlik varkən silmək TƏHLÜKƏLİDİR: hesab gedər, Paddle isə
    # pul çəkməyə davam edər və istifadəçinin onu dayandırmaq üçün girişi
    # qalmaz. Provayderin API açarımız abunəliyi ləğv etməyə icazə vermir,
    # ona görə istifadəçini portala yönləndiririk.
    if (user.subscription_status or "").lower() in {"active", "trialing", "past_due"}:
        provider = payments.get_payments()
        url = provider.manage_url(subscription_id=user.subscription_id) if provider else None
        raise HTTPException(
            status_code=409,
            detail={
                "error": "subscription_active",
                "message": "Əvvəlcə abunəliyi ləğv et, sonra hesabı silmək olar.",
                "manage_url": url,
            },
        )

    if user.deletion_requested_at is None:
        user.deletion_requested_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
    return _user_out(db, user)


@router.post("/account/delete/cancel", response_model=UserOut)
def cancel_deletion(
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_user),
):
    """Möhlət bitməmişdən əvvəl tələbi geri götürür."""
    user.deletion_requested_at = None
    db.commit()
    db.refresh(user)
    return _user_out(db, user)


@router.post("/account/purge", dependencies=[Depends(require_admin_key)])
def purge_deleted(db: Session = Depends(get_db)):
    """Möhləti bitmiş hesabları HƏQİQƏTƏN silir. Cron gündə bir dəfə çağırır.

    Sətrin silinməsi kifayətdir, çünki xarici açarlar düzgün qurulub:
      user_sessions, saved_papers, usage_events, documents  -> CASCADE
      document_chunks                                       -> documents-dən CASCADE
      billing_events                                        -> SET NULL

    Sonuncusu qəsdəndir: maliyyə qeydi mühasibat üçün qalmalıdır, amma
    istifadəçi ilə bağlantısı qırılır. Yəni «kim ödədi» itir, «nə qədər
    ödənilib» qalır.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.account_deletion_grace_days)
    rows = (
        db.query(models.User)
        .filter(
            models.User.deletion_requested_at.isnot(None),
            models.User.deletion_requested_at <= cutoff,
        )
        .all()
    )
    purged = [{"id": u.id, "requested_at": u.deletion_requested_at} for u in rows]
    for u in rows:
        db.delete(u)
    db.commit()
    return {"purged": len(purged), "grace_days": settings.account_deletion_grace_days,
            "accounts": purged}
