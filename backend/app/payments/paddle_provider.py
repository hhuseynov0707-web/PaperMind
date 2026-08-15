"""Paddle Billing (v2) adapteri.

Paddle seçildi, çünki **Stripe Azərbaycanda satıcı hesabı açmır**. Paddle
*Merchant of Record*-dur: satış hüquqi olaraq onun üzərindən gedir və ƏDV/satış
vergisini o hesablayıb ödəyir. Tək adam üçün bu, seçim deyil, zərurətdir —
Aİ ƏDV-si ölkə-ölkə hesablanmalıdır və bunu əl ilə aparmaq mümkün deyil.
"""

import hashlib
import hmac
import time
from datetime import datetime, timezone

from ..config import settings
from .base import BillingUpdate

# İmza vaxtı bu qədər köhnədirsə hadisə rədd olunur — təkrar oynatma (replay)
# hücumuna qarşı. Paddle-ın öz tövsiyəsi 5 dəqiqədir.
_MAX_SIGNATURE_AGE = 300

# Abunə statusundan bizim plana xəritə. `active` və `trialing` Pro sayılır;
# `past_due` DƏ Pro qalır — ödəniş gecikəndə istifadəçini dərhal kəsmək
# müştəri itirməyin ən sürətli yoludur, provayder isə təkrar cəhd edir.
_PRO_STATUSES = {"active", "trialing", "past_due"}


class PaddleProvider:
    name = "paddle"

    def __init__(self) -> None:
        self.api_key = settings.paddle_api_key            # gizli, server tərəfli
        self.client_token = settings.paddle_client_token  # brauzerə düşür, gizli deyil
        self.webhook_secret = settings.paddle_webhook_secret
        self.price_id = settings.paddle_price_id_pro
        self.sandbox = settings.paddle_environment != "production"

    # --- Checkout ---------------------------------------------------------

    def checkout_url(self, *, user_id: int, email: str, plan_key: str, return_url: str) -> str:
        """Paddle-ın öz checkout-u frontend-də (Paddle.js) açılır.

        Burada tam URL qurmuruq: Paddle Billing-də tövsiyə olunan yol
        `Paddle.Checkout.open({...})` çağırışıdır. Server yalnız checkout üçün
        lazım olan parametrləri verir — `custom_data.user_id` webhook-da geri
        qayıdır və hesabı məhz bununla tapırıq.
        """
        raise NotImplementedError(
            "Paddle checkout frontend-də Paddle.js ilə açılır — /api/billing/checkout "
            "parametrləri qaytarır, URL yox."
        )

    def checkout_params(self, *, user_id: int, email: str, return_url: str) -> dict:
        return {
            "provider": self.name,
            "environment": "sandbox" if self.sandbox else "production",
            # Yalnız client token verilir — API açarı HEÇ VAXT frontend-ə düşmür.
            "client_token": self.client_token,
            "price_id": self.price_id,
            "customer_email": email,
            # Webhook-da geri qayıdır. E-poçtla uyğunlaşdırmaq TƏHLÜKƏLİDİR:
            # istifadəçi ödənişi başqa e-poçtla edə bilər və yanlış hesab
            # Pro olardı.
            "custom_data": {"user_id": str(user_id)},
            "return_url": return_url,
        }

    # --- Webhook ----------------------------------------------------------

    def verify_webhook(self, raw_body: bytes, signature_header: str | None) -> bool:
        """`Paddle-Signature: ts=<unix>;h1=<hex>` formatı.

        İmzalanan mətn `<ts>:<xam gövdə>`-dir. Gövdə **xam** olmalıdır —
        JSON-u parse edib yenidən seriallaşdırsaq baytlar dəyişir və imza
        heç vaxt tutmaz.
        """
        if not self.webhook_secret or not signature_header:
            return False

        parts = dict(
            piece.split("=", 1)
            for piece in signature_header.split(";")
            if "=" in piece
        )
        ts, received = parts.get("ts"), parts.get("h1")
        if not ts or not received:
            return False

        try:
            age = abs(time.time() - int(ts))
        except ValueError:
            return False
        if age > _MAX_SIGNATURE_AGE:
            return False

        expected = hmac.new(
            self.webhook_secret.encode(),
            f"{ts}:".encode() + raw_body,
            hashlib.sha256,
        ).hexdigest()

        # Sabit müddətli müqayisə — adi `==` imzanı bayt-bayt təxmin etməyə
        # imkan verən vaxt sızması yaradır.
        return hmac.compare_digest(expected, received)

    def parse_event(self, payload: dict) -> BillingUpdate | None:
        event_type = payload.get("event_type") or ""
        if not event_type.startswith("subscription."):
            return None

        data = payload.get("data") or {}
        custom = data.get("custom_data") or {}
        raw_uid = custom.get("user_id")
        try:
            user_id = int(raw_uid) if raw_uid is not None else None
        except (TypeError, ValueError):
            user_id = None

        status = data.get("status")
        expires_at = _parse_time(
            (data.get("current_billing_period") or {}).get("ends_at")
        )

        # `subscription.canceled` gələndə status sahəsi bəzən hələ `active`
        # olur — hadisə tipi statusdan ÜSTÜNdür.
        if event_type == "subscription.canceled":
            plan = "free"
        else:
            plan = "pro" if status in _PRO_STATUSES else "free"

        return BillingUpdate(
            event_id=payload.get("event_id") or "",
            event_type=event_type,
            user_id=user_id,
            customer_id=data.get("customer_id"),
            subscription_id=data.get("id"),
            status=status,
            plan=plan,
            expires_at=expires_at,
            raw=payload,
        )

    def manage_url(self, *, subscription_id: str) -> str | None:
        # Paddle idarəetmə linkini API-dən verir; hazırda çağırmırıq, çünki
        # bu, API açarı ilə şəbəkə sorğusu tələb edir və hələ lazım deyil.
        return None


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None
