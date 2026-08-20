"""Hesabın silinməsi — §17 (GDPR «unudulma hüququ»).

Bu axının səhvinin qiyməti asimmetrikdir: silmə İŞLƏMƏSƏ hüquqi problem,
YANLIŞ işləsə isə istifadəçinin bütün kitabxanası, sənədləri və tarixçəsi
geri qaytarılmadan gedir. Ona görə testlər hər iki tərəfə baxır.

Kaskad davranışı burada YOXLANILMIR — o, Python məntiqi deyil, xarici açar
qaydasıdır (`ON DELETE CASCADE` / `SET NULL`). Mock baza onu təqlid etsə,
test yalan danışardı: keçər, istehsalatda isə məlumat qalardı. Kaskad real
Postgres üzərində ayrıca sübut olunur (bax `scripts/verify-deletion.sh`).
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import auth, models
from app.config import settings
from app.database import get_db
from app.main import app
from app.routers.accounts import _effective_at


# --- Möhlət hesabı ----------------------------------------------------------

def test_effective_date_is_computed_from_the_request():
    """İnterfeys «X tarixində silinəcək» yazır. Tarix SERVERDƏ hesablanır —
    frontend-də ikinci dəfə hesablansaydı, möhlət dəyişəndə interfeys
    səssizcə yalan danışardı."""
    u = MagicMock()
    u.deletion_requested_at = datetime(2026, 8, 20, tzinfo=timezone.utc)
    got = _effective_at(u)
    assert got == u.deletion_requested_at + timedelta(days=settings.account_deletion_grace_days)


def test_no_request_means_no_effective_date():
    u = MagicMock()
    u.deletion_requested_at = None
    assert _effective_at(u) is None


def test_grace_period_is_not_zero():
    """Möhlət sıfır olsaydı, təsadüfi klik dərhal hər şeyi aparardı."""
    assert settings.account_deletion_grace_days >= 7


# --- Endpoint davranışı -----------------------------------------------------

@pytest.fixture
def user():
    u = models.User(
        id=7, email="a@x.com", password_hash=auth.hash_password("duzgun-parol-123"),
        plan="free", is_active=True, credits_used=0,
    )
    u.deletion_requested_at = None
    u.subscription_status = None
    u.subscription_id = None
    u.created_at = datetime.now(timezone.utc)
    u.plan_expires_at = None
    u.display_name = None
    return u


@pytest.fixture
def client(user):
    db = MagicMock()
    db.query.return_value.filter.return_value.count.return_value = 0
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[auth.require_user] = lambda: user
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def test_wrong_password_does_not_mark_the_account(client, user):
    """Ən vacib test.

    Sessiya oğurlanıbsa və ya kimsə açıq kompüterə yaxınlaşıbsa, tək klik
    hesabı silməyə kifayət etməməlidir.
    """
    r = client.post("/api/auth/account/delete", json={"password": "yanlis-parol-999"})
    assert r.status_code == 401
    assert user.deletion_requested_at is None      # HEÇ NƏ dəyişməyib


def test_correct_password_marks_but_does_not_delete(client, user):
    r = client.post("/api/auth/account/delete", json={"password": "duzgun-parol-123"})
    assert r.status_code == 200
    assert user.deletion_requested_at is not None
    assert user.is_active is True                  # sətir HƏLƏ yerindədir


def test_response_tells_the_user_when_it_happens(client, user):
    r = client.post("/api/auth/account/delete", json={"password": "duzgun-parol-123"})
    body = r.json()
    assert body["deletion_requested_at"] is not None
    assert body["deletion_effective_at"] is not None
    assert body["deletion_effective_at"] > body["deletion_requested_at"]


def test_repeat_request_does_not_restart_the_clock(client, user):
    """İkinci dəfə basmaq möhləti uzatmamalıdır — əks halda istifadəçi
    təsadüfən öz silinməsini sonsuz təxirə salardı."""
    client.post("/api/auth/account/delete", json={"password": "duzgun-parol-123"})
    first = user.deletion_requested_at
    client.post("/api/auth/account/delete", json={"password": "duzgun-parol-123"})
    assert user.deletion_requested_at == first


def test_cancel_clears_the_request(client, user):
    client.post("/api/auth/account/delete", json={"password": "duzgun-parol-123"})
    assert user.deletion_requested_at is not None
    r = client.post("/api/auth/account/delete/cancel")
    assert r.status_code == 200
    assert user.deletion_requested_at is None


# --- Aktiv abunəlik ---------------------------------------------------------

@pytest.mark.parametrize("status", ["active", "ACTIVE", "trialing", "past_due"])
def test_active_subscription_blocks_deletion(client, user, status):
    """"Hesab silindi, pul çəkilməyə davam edir" ən pis nəticədir:
    istifadəçinin onu dayandırmaq üçün girişi də qalmır."""
    user.subscription_status = status
    r = client.post("/api/auth/account/delete", json={"password": "duzgun-parol-123"})
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "subscription_active"
    assert user.deletion_requested_at is None


@pytest.mark.parametrize("status", ["canceled", "paused", None, ""])
def test_inactive_subscription_does_not_block(client, user, status):
    user.subscription_status = status
    r = client.post("/api/auth/account/delete", json={"password": "duzgun-parol-123"})
    assert r.status_code == 200


# --- Səlahiyyət -------------------------------------------------------------

def test_purge_requires_admin_key(monkeypatch):
    """Möhləti bitmiş hesabları silən uc ictimai olsaydı, istənilən adam
    onu çağırıb silinməni tezləşdirə bilərdi.

    `public_mode` açılır, çünki `require_admin_key` lokal rejimdə qorumanı
    QƏSDƏN ötürür (geliştirmə rahatlığı üçün). İstehsalatda o, açıqdır —
    yoxlanılıb: `POST /api/ingest` açarsız 401 qaytarır.
    """
    monkeypatch.setattr(settings, "public_mode", True)
    monkeypatch.setattr(settings, "admin_api_key", "test-acar")
    app.dependency_overrides.clear()
    c = TestClient(app, raise_server_exceptions=False)
    assert c.post("/api/auth/account/purge").status_code == 401
    assert c.post("/api/auth/account/purge",
                  headers={"X-API-Key": "yanlis"}).status_code == 401


def test_delete_requires_login():
    app.dependency_overrides.clear()
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/api/auth/account/delete", json={"password": "x"})
    assert r.status_code == 401
