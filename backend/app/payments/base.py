"""Ödəniş provayderi müqaviləsi — §18 ilə eyni yanaşma.

Biznes məntiqi «Paddle» sözünü görmür. Provayder dəyişəndə (məsələn ölkə
dəstəyi açılıb Stripe-a keçmək mümkün olanda) yalnız bu qovluğa yeni fayl
əlavə olunur.

`Protocol` seçilib, ABC yox: provayder bizim sinifdən törəmək məcburiyyətində
qalmasın, testdə sadə saxta sinif kifayət etsin.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass
class BillingUpdate:
    """Webhook-dan çıxarılan, provayderdən ASILI OLMAYAN nəticə.

    `user_id` checkout zamanı göndərdiyimiz `custom_data`-dan qayıdır — e-poçt
    üzrə uyğunlaşdırmaq təhlükəlidir, çünki istifadəçi ödənişi başqa e-poçtla
    edə bilər və o zaman yanlış hesab Pro olardı.
    """

    event_id: str
    event_type: str
    user_id: int | None = None
    customer_id: str | None = None
    subscription_id: str | None = None
    status: str | None = None            # active | canceled | past_due | paused
    plan: str | None = None              # bizim daxili plan açarı
    expires_at: datetime | None = None
    raw: dict = field(default_factory=dict)


@runtime_checkable
class PaymentProvider(Protocol):
    name: str

    def checkout_url(self, *, user_id: int, email: str, plan_key: str, return_url: str) -> str:
        """Ödəniş səhifəsinin ünvanı. `user_id` webhook-da geri qayıtmalıdır."""
        ...

    def verify_webhook(self, raw_body: bytes, signature_header: str | None) -> bool:
        """İmza yoxlaması. False qaytarsa hadisə EMAL EDİLMİR."""
        ...

    def parse_event(self, payload: dict) -> BillingUpdate | None:
        """Bizə aid olmayan hadisə üçün None."""
        ...

    def manage_url(self, *, subscription_id: str) -> str | None:
        """Abunəni idarə etmə/ləğv səhifəsi, varsa."""
        ...
