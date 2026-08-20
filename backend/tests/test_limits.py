"""Sürət limitləri — §qoruma.

Bu testlər «limit işləyirmi» yox, «limit DOĞRU ŞEYƏ görə ayrılırmı»
sualına cavab verir. Fərq praktikdir: yalnız IP üzrə sayan limit botnet
qarşısında heç nə etmir, yalnız hesab üzrə sayan limit isə hücumçuya
qurbanın hesabını kilidləmək imkanı verir.
"""

import pytest

from app import limits


class FakeRedis:
    """Üç metodluq saxta Redis.

    `fakeredis` paketi əlavə etmədik: bura yalnız `incr`, `expire` və `ttl`
    lazımdır. Test üçün bütöv bir asılılıq gətirmək həm quraşdırma yükü,
    həm də təchizat zənciri səthidir — üç metodu özümüz yazmaq ucuzdur.
    """

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def expire(self, key: str, seconds: int) -> None:
        self.ttls[key] = seconds

    def ttl(self, key: str) -> int:
        return self.ttls.get(key, -1)


@pytest.fixture(autouse=True)
def _redis(monkeypatch):
    """Hər test təmiz sayğaclarla başlayır; `public_mode` açıq olmalıdır."""
    monkeypatch.setattr(limits, "_r", FakeRedis())
    monkeypatch.setattr(limits.settings, "public_mode", True)


def _login(ip: str, account: str) -> None:
    limits.enforce("login", ip=ip, account=account)


# --- Əhatə ayrılığı --------------------------------------------------------

def test_login_limit_is_per_ip():
    limit = limits.RULES["login"][0].limit
    for _ in range(limit):
        _login("1.1.1.1", "a@x.com")
    with pytest.raises(Exception) as exc:
        _login("1.1.1.1", "a@x.com")
    assert exc.value.status_code == 429


def test_different_ip_is_not_punished_for_someone_elses_attempts():
    """Bir ünvanın limiti başqasını bloklamamalıdır — yoxsa ortaq NAT
    arxasındakı bütün istifadəçilər bir nəfərə görə kilidlənər."""
    for _ in range(limits.RULES["login"][0].limit):
        _login("1.1.1.1", "a@x.com")
    _login("2.2.2.2", "b@x.com")          # atmamalıdır


def test_botnet_hitting_one_account_from_many_ips_is_stopped():
    """Ən vacib test.

    Yalnız IP limiti olsaydı, hücumçu hər ünvandan BİR parol sınayıb
    limitə heç vaxt dəyməzdi. Hesab sayğacı məhz bunu bağlayır.
    """
    limit = limits.RULES["login"][1].limit
    for i in range(limit):
        _login(f"10.0.0.{i}", "qurban@x.com")     # hər dəfə YENİ ünvan
    with pytest.raises(Exception) as exc:
        _login("10.0.0.99", "qurban@x.com")
    assert exc.value.status_code == 429


def test_account_counter_is_case_and_space_insensitive():
    """`A@X.com ` ilə `a@x.com` eyni hesabdır — normallaşdırmasaq, hücumçu
    böyük hərflə yazıb sayğacı sıfırdan başladar."""
    limit = limits.RULES["login"][1].limit
    for i in range(limit):
        _login(f"10.1.0.{i}", "  QURBAN@X.com ")
    with pytest.raises(Exception):
        _login("10.1.0.99", "qurban@x.com")


# --- İstifadəçiyə deyilən vaxt --------------------------------------------

def test_message_says_how_long_to_wait_and_sets_retry_after():
    """Sabit «bir saat sonra» mətni pəncərə dəyişəndə yalan olur.
    Mesaj Redis-dəki REAL qalan vaxtdan qurulmalıdır."""
    for _ in range(limits.RULES["signup"][0].limit):
        limits.enforce("signup", ip="3.3.3.3", account="a@x.com")
    with pytest.raises(Exception) as exc:
        limits.enforce("signup", ip="3.3.3.3", account="a@x.com")

    err = exc.value
    assert "Retry-After" in err.headers
    assert int(err.headers["Retry-After"]) > 0
    # Pəncərə 1 saatdır, ona görə mesajda «saat» və ya «dəqiqə» keçməlidir
    assert "saat" in err.detail or "dəqiqə" in err.detail


@pytest.mark.parametrize("seconds,expected", [
    (5, "bir dəqiqədən az"), (60, "bir dəqiqədən az"),
    (600, "10 dəqiqə"), (3600, "bir saat"), (7200, "2 saat"),
])
def test_wait_description_is_human_readable(seconds, expected):
    assert limits._describe(seconds) == expected


# --- Fail-open davranışı ---------------------------------------------------

def test_redis_failure_does_not_lock_everyone_out(monkeypatch):
    """Keş nasazlığı bütün girişi dayandırmamalıdır.

    Bu, ŞÜURLU güzəştdir: limit qorumadır, autentifikasiya deyil. Redis
    düşəndə parol yoxlaması yerindədir; limitin ötürülməsi isə saytın
    tamamilə çökməsindən yaxşıdır.
    """
    class Broken:
        def incr(self, *a): raise RuntimeError("redis down")
        def expire(self, *a): raise RuntimeError("redis down")
        def ttl(self, *a): raise RuntimeError("redis down")

    monkeypatch.setattr(limits, "_r", Broken())
    for _ in range(50):
        _login("4.4.4.4", "a@x.com")          # heç biri atmamalıdır


def test_local_mode_has_no_limits(monkeypatch):
    monkeypatch.setattr(limits.settings, "public_mode", False)
    for _ in range(100):
        _login("5.5.5.5", "a@x.com")


# --- Qaydaların özü --------------------------------------------------------

def test_every_rule_has_a_positive_window_and_known_scope():
    """Səhv yazılmış qayda səssizcə atlanır (`values.get(scope)` -> None),
    yəni limit heç vaxt işə düşmür və bunu kimsə görmür."""
    known = {"ip", "account", "user", "global"}
    for name, rules in limits.RULES.items():
        assert rules, f"{name}: qayda siyahısı boşdur"
        for r in rules:
            assert r.scope in known, f"{name}: naməlum əhatə {r.scope!r}"
            assert r.limit > 0 and r.window > 0, f"{name}: mənasız hədd/pəncərə"


def test_login_is_limited_on_both_ip_and_account():
    """Qaydanın özü silinsə, yuxarıdakı davranış testləri də düşər — amma
    bu test səbəbi birbaşa adlandırır."""
    scopes = {r.scope for r in limits.RULES["login"]}
    assert scopes == {"ip", "account"}
