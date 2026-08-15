"""Ödəniş provayderi reyestri — `providers/__init__.py` ilə eyni quruluş."""

from ..config import settings
from .base import BillingUpdate, PaymentProvider
from .paddle_provider import PaddleProvider

_REGISTRY: dict[str, type] = {"paddle": PaddleProvider}

_cache: dict[str, object] = {}


def register(name: str, cls: type) -> None:
    _REGISTRY[name] = cls
    _cache.pop(name, None)


def get_payments(name: str | None = None):
    """Provayder nümunəsi. `PAYMENT_PROVIDER` boşdursa None — ödəniş sönülüdür.

    None qaytarmaq qəsdəndir: ödəniş qurulmamış mühitdə (lokal iş, test) bütün
    tətbiq işləməyə davam etməlidir, yalnız billing endpoint-ləri 503 verir.
    """
    key = name or settings.payment_provider
    if not key:
        return None
    if key not in _REGISTRY:
        raise ValueError(f"Naməlum ödəniş provayderi: {key}")
    if key not in _cache:
        _cache[key] = _REGISTRY[key]()
    return _cache[key]


__all__ = ["BillingUpdate", "PaymentProvider", "get_payments", "register"]
