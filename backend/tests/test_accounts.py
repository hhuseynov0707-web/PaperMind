"""Hesab, plan və ödəniş qatının testləri.

Diqqət yönü: bu qatda səhvin qiyməti fərqlidir. Retrieval-də səhv nəticə pis
cavab verir; burada səhv ya pulsuz istifadəçini Pro edir, ya da kənar adama
başqasının hesabını açır. Ona görə testlər «işləyirmi» yox, «SINDIRILA
BİLİRMİ» sualını verir.
"""

import hashlib
import hmac
import json
import time
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import auth, plans
from app.config import settings
from app.database import get_db
from app.main import app
from app.payments.paddle_provider import PaddleProvider


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = lambda: MagicMock()
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


# --- Parol ------------------------------------------------------------------

def test_password_roundtrip():
    h = auth.hash_password("duzgun-parol-123")
    assert auth.verify_password(h, "duzgun-parol-123")
    assert not auth.verify_password(h, "yanlis-parol-123")


def test_password_hash_is_not_the_password():
    """Həsh içində açıq parol qalmamalıdır — sadə, amma unudulan yoxlama."""
    h = auth.hash_password("cox-gizli-parol")
    assert "cox-gizli-parol" not in h
    assert h.startswith("$argon2")


def test_same_password_gives_different_hashes():
    """Duz təsadüfidir: eyni parol iki fərqli həsh verməlidir.

    Bərabər olsalar, sızmış bazada eyni parolu işlədən hesablar bir baxışda
    görünərdi.
    """
    assert auth.hash_password("eyni-parol-123") != auth.hash_password("eyni-parol-123")


def test_short_password_rejected():
    assert auth.password_problem("qisa") is not None
    assert auth.password_problem("a" * settings.min_password_length) is None


def test_corrupted_hash_is_not_authentication():
    """Korlanmış həsh 500 yox, «yanlış parol» verməlidir."""
    assert not auth.verify_password("bu-hesh-deyil", "istenilen")


def test_email_normalized():
    assert auth.normalize_email("  Ali@Example.COM ") == "ali@example.com"
    assert auth.valid_email("ali@example.com")
    assert not auth.valid_email("ali@example")
    assert not auth.valid_email("bosluq var@example.com")


# --- Plan və imkan ----------------------------------------------------------

def test_unknown_plan_falls_back_to_free():
    """Təhlükəsizlik xassəsi: naməlum dəyər HEÇ VAXT yuxarı qalxmamalıdır.

    Baza korlansa və ya webhook zibil yazsa, nəticə pulsuz olmalıdır.
    """
    for bad in (None, "", "PRO", "premium", "admin", "pro "):
        assert plans.get_plan(bad).key == plans.FREE


def test_free_plan_lacks_pro_capabilities():
    free = plans.get_plan(plans.FREE)
    pro = plans.get_plan(plans.PRO)
    for cap in (plans.UPLOAD_PDF, plans.ASK_LIBRARY, plans.GAPS, plans.CONFLICTS):
        assert cap not in free.capabilities
        assert cap in pro.capabilities


def test_free_plan_still_delivers_value():
    """Pulsuz qat boş olmamalıdır — yoxsa qeydiyyatın mənası yoxdur."""
    free = plans.get_plan(plans.FREE)
    assert plans.ASK in free.capabilities
    assert plans.SAVE in free.capabilities
    assert free.monthly_credits > 0


def test_expensive_actions_cost_more():
    assert plans.cost_of(plans.ASK) < plans.cost_of(plans.COMPARE)
    assert plans.cost_of(plans.COMPARE) < plans.cost_of(plans.GAPS)
    assert plans.cost_of(plans.SAVE) == 0


# --- Endpoint qorunması -----------------------------------------------------

def test_ask_requires_login(client):
    """Ən bahalı endpoint girişsiz açıq qalmamalıdır."""
    r = client.post("/api/ask", json={"question": "transformer nedir?"})
    assert r.status_code == 401


def test_library_requires_login(client):
    # Tam siyahı `test_library.py`-dədir; burada yalnız giriş qapısı yoxlanılır.
    assert client.get("/api/library").status_code == 401
    assert client.put("/api/library/1", json={"saved": True}).status_code == 401


def test_me_requires_login(client):
    assert client.get("/api/auth/me").status_code == 401


def test_plans_are_public(client):
    """Qiymət səhifəsi girişsiz görünməlidir — əks halda heç kim qeydiyyatdan
    keçməzdən əvvəl nə aldığını bilmir."""
    r = client.get("/api/auth/plans")
    assert r.status_code == 200
    keys = {p["key"] for p in r.json()}
    assert keys == {plans.FREE, plans.PRO}


def test_plans_never_leak_capabilities_as_prices(client):
    """Qiymət provayderdədir — cavabda qiymət sahəsi OLMAMALIDIR.

    İki yerdə saxlanılsa, saytda bir rəqəm, checkout-da başqası görünər.
    """
    body = client.get("/api/auth/plans").json()
    for plan in body:
        assert "price" not in plan
        assert "amount" not in plan


@pytest.fixture
def as_free_user():
    """Girişli, amma PULSUZ istifadəçi.

    `require_capability` daxildə `require_user`-dən asılıdır, ona görə yalnız
    onu əvəzləmək kifayətdir — imkan yoxlaması real plan matrisi üzərində işləyir.
    """
    from app import models
    from app.auth import require_user

    app.dependency_overrides[require_user] = lambda: models.User(
        id=1, email="free@example.com", password_hash="x", plan=plans.FREE
    )
    yield
    app.dependency_overrides.pop(require_user, None)


def test_free_user_blocked_from_pro_endpoints(client, as_free_user):
    """Pulsuz istifadəçi Pro imkanına çatmamalıdır — 402, 401 yox.

    Bu, gating-in ƏSL yoxlanışıdır: `plans.py`-da imkanı Pro elan edib
    endpoint-ə tətbiq etməyi unutmaq görünməyən sızmadır.
    """
    r = client.post("/api/conflicts", json=[1, 2])
    assert r.status_code == 402
    assert r.json()["detail"]["error"] == "upgrade_required"

    r = client.get("/api/gaps", params={"q": "transformer"})
    assert r.status_code == 402


def test_free_user_allowed_on_free_endpoints(client, as_free_user):
    """Pulsuz qat boş olmamalıdır — müqayisə 402 QAYTARMAMALIDIR.

    (Ardınca DB/LLM lazım olduğu üçün başqa xəta gələ bilər; ölçdüyümüz şey
    yalnız imkan qapısının açıq olmasıdır.)
    """
    r = client.post("/api/compare", json=[1, 2])
    assert r.status_code != 402


# --- Paddle webhook imzası --------------------------------------------------

SECRET = "pdl_ntfset_test_secret"


def _provider() -> PaddleProvider:
    old = settings.paddle_webhook_secret
    settings.paddle_webhook_secret = SECRET
    try:
        return PaddleProvider()
    finally:
        settings.paddle_webhook_secret = old


def _sign(body: bytes, ts: int | None = None) -> str:
    ts = ts or int(time.time())
    digest = hmac.new(SECRET.encode(), f"{ts}:".encode() + body, hashlib.sha256).hexdigest()
    return f"ts={ts};h1={digest}"


def test_valid_signature_accepted():
    p = _provider()
    body = json.dumps({"event_id": "evt_1"}).encode()
    assert p.verify_webhook(body, _sign(body))


def test_tampered_body_rejected():
    """İmza gövdə üzərindədir: bir bayt dəyişsə keçməməlidir."""
    p = _provider()
    body = json.dumps({"event_id": "evt_1"}).encode()
    sig = _sign(body)
    assert not p.verify_webhook(body + b" ", sig)


def test_missing_signature_rejected():
    p = _provider()
    assert not p.verify_webhook(b"{}", None)
    assert not p.verify_webhook(b"{}", "")
    assert not p.verify_webhook(b"{}", "zibil")


def test_replayed_old_signature_rejected():
    """Köhnə, amma DÜZGÜN imza qəbul edilməməlidir — təkrar oynatma hücumu."""
    p = _provider()
    body = b'{"event_id":"evt_old"}'
    old_ts = int(time.time()) - 3600
    assert not p.verify_webhook(body, _sign(body, ts=old_ts))


def test_signature_without_secret_always_fails():
    """Sirr qurulmayıbsa webhook AÇIQ qalmamalıdır — hamısı rədd olunur."""
    old = settings.paddle_webhook_secret
    settings.paddle_webhook_secret = ""
    try:
        p = PaddleProvider()
        body = b"{}"
        assert not p.verify_webhook(body, _sign(body))
    finally:
        settings.paddle_webhook_secret = old


# --- Webhook məzmununun yozulması -------------------------------------------

def _event(event_type: str, status: str, user_id: str | None = "7") -> dict:
    data: dict = {"id": "sub_1", "status": status, "customer_id": "ctm_1"}
    if user_id is not None:
        data["custom_data"] = {"user_id": user_id}
    return {"event_id": "evt_x", "event_type": event_type, "data": data}


def test_active_subscription_becomes_pro():
    upd = _provider().parse_event(_event("subscription.activated", "active"))
    assert upd is not None
    assert upd.plan == plans.PRO
    assert upd.user_id == 7


def test_canceled_event_downgrades_even_if_status_still_active():
    """Paddle ləğv hadisəsində statusu bəzən hələ `active` göndərir.

    Hadisə tipi statusdan üstün olmasa, ləğv edən istifadəçi Pro qalardı.
    """
    upd = _provider().parse_event(_event("subscription.canceled", "active"))
    assert upd is not None and upd.plan == plans.FREE


def test_past_due_stays_pro():
    """Ödəniş gecikəndə dərhal kəsmək müştəri itirməyin ən sürətli yoludur —
    provayder təkrar cəhd edir."""
    upd = _provider().parse_event(_event("subscription.past_due", "past_due"))
    assert upd is not None and upd.plan == plans.PRO


def test_event_without_user_id_is_not_applied_blindly():
    """`custom_data` yoxdursa hesab təyin edilə bilmir — user_id None qalmalıdır.

    E-poçtla uyğunlaşdırmaq TƏHLÜKƏLİDİR: istifadəçi ödənişi başqa e-poçtla
    edə bilər və yanlış hesab Pro olardı.
    """
    upd = _provider().parse_event(_event("subscription.activated", "active", user_id=None))
    assert upd is not None and upd.user_id is None


def test_non_subscription_events_ignored():
    assert _provider().parse_event({"event_type": "transaction.paid", "data": {}}) is None


def test_garbage_user_id_does_not_crash():
    upd = _provider().parse_event(_event("subscription.activated", "active", user_id="abc"))
    assert upd is not None and upd.user_id is None
