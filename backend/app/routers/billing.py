"""Abunə: checkout parametrləri və provayder webhook-u.

Plan DƏYİŞİKLİYİ yalnız webhook-dan gəlir — heç bir istifadəçi sorğusu planı
qaldıra bilmir. «Ödədim» deyən frontend çağırışına inanmaq, ödəniş sistemini
tamamilə mənasız edən klassik səhvdir.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from .. import models, payments, plans
from ..auth import require_user
from ..config import settings
from ..database import get_db
from ..schemas import CheckoutOut

router = APIRouter(prefix="/api/billing", tags=["billing"])


def _base_url(request: Request) -> str:
    return (settings.public_base_url or str(request.base_url)).rstrip("/")


@router.get("/checkout", response_model=CheckoutOut)
def checkout(
    request: Request,
    user: models.User = Depends(require_user),
):
    provider = payments.get_payments()
    if provider is None:
        raise HTTPException(
            status_code=503,
            detail="Ödəniş hazırda aktiv deyil (PAYMENT_PROVIDER təyin olunmayıb).",
        )
    if user.plan == plans.PRO:
        raise HTTPException(status_code=409, detail="Artıq Pro planındasan.")
    if not settings.paddle_price_id_pro:
        raise HTTPException(
            status_code=503, detail="Plan qiyməti konfiqurasiya olunmayıb."
        )

    params = provider.checkout_params(
        user_id=user.id,
        email=user.email,
        return_url=f"{_base_url(request)}/?upgraded=1",
    )
    return CheckoutOut(**params)


@router.post("/webhook", status_code=200)
async def webhook(
    request: Request,
    db: Session = Depends(get_db),
    paddle_signature: str | None = Header(default=None, alias="Paddle-Signature"),
):
    """Provayderdən gələn abunə hadisələri.

    Üç qoruma var və üçü də vacibdir:
      1. **İmza** — yoxsa istənilən adam POST atıb özünü Pro edə bilər.
      2. **İdempotentlik** — provayder eyni hadisəni təkrar göndərir; `event_id`
         unikal olduğu üçün ikincisi emal olunmur.
      3. **Xam gövdə** — imza baytlar üzərində hesablanır, parse edilmiş JSON
         üzərində yox.
    """
    provider = payments.get_payments()
    if provider is None:
        raise HTTPException(status_code=503, detail="Ödəniş provayderi aktiv deyil.")

    raw = await request.body()
    if not provider.verify_webhook(raw, paddle_signature):
        # 400, 401 yox: provayder 401-i «yenidən cəhd et» kimi yozmasın.
        raise HTTPException(status_code=400, detail="İmza yoxlanışı keçmədi.")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Gövdə JSON deyil.")

    update = provider.parse_event(payload)
    if update is None or not update.event_id:
        return {"status": "ignored"}

    # İdempotentlik: eyni hadisə ikinci dəfə gəlsə heç nə etmir.
    seen = (
        db.query(models.BillingEvent)
        .filter(models.BillingEvent.event_id == update.event_id)
        .first()
    )
    if seen is not None:
        return {"status": "duplicate"}

    user = db.get(models.User, update.user_id) if update.user_id else None

    db.add(
        models.BillingEvent(
            event_id=update.event_id,
            event_type=update.event_type,
            user_id=user.id if user else None,
            payload=payload,
        )
    )

    if user is None:
        # Hadisə qeyd olunur, amma heç bir hesaba tətbiq edilmir. Bu, səssiz
        # uğursuzluq deyil — sətir bazada qalır və araşdırıla bilir.
        db.commit()
        return {"status": "recorded_without_user"}

    user.plan = update.plan or plans.FREE
    user.subscription_id = update.subscription_id
    user.subscription_status = update.status
    user.plan_expires_at = update.expires_at
    if update.customer_id:
        user.billing_customer_id = update.customer_id
    db.commit()

    return {"status": "applied", "plan": user.plan}


@router.get("/usage")
def usage(
    limit: int = 30,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    """İstifadəçi öz kredit xərcini görə bilməlidir — «kreditim niyə bitdi?»
    sualının cavabı interfeysdə olmalıdır, dəstək yazışmasında yox."""
    rows = (
        db.query(models.UsageEvent)
        .filter(models.UsageEvent.user_id == user.id)
        .order_by(models.UsageEvent.created_at.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )
    period = datetime.now(timezone.utc).strftime("%Y%m")
    return {
        "period": period,
        "used": user.credits_used if user.credits_period == period else 0,
        "total": plans.get_plan(user.plan).monthly_credits,
        "events": [
            {"action": r.action, "credits": r.credits, "created_at": r.created_at}
            for r in rows
        ],
    }
