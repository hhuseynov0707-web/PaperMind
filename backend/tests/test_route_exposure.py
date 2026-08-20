"""Hər marşrutun açıq olub-olmadığı BİLƏRƏKDƏN qərar olmalıdır.

Bu testin doğulma səbəbi konkretdir: `GET /api/logs/questions` internetdə
hər kəsə bütün istifadəçi suallarını qaytarırdı. Kimsə pis niyyətlə açıq
qoymamışdı — sadəcə `POST /logs/error`-a mühafizə əlavə edilmiş, üç `GET`
isə unudulmuşdu. Qorunma endpoint-in fərdi seçimi olanda, unutmaq üçün bir
dəfə diqqətsizlik kifayətdir.

Ona görə burada sıra tərsinə çevrilir: **standart RƏDD**. Marşrut ya
aşağıdakı siyahıda açıqca sadalanır, ya da mühafizə asılılığı daşımalıdır.
Yeni endpoint yazan adam heç nə etməsə, test düşür — səhv təhlükəsiz
tərəfə yıxılır.

Niyə runtime middleware yox?
    Middleware autentifikasiyanı İKİNCİ dəfə tətbiq etməli olardı: sessiya
    oxumaq, açar yoxlamaq, plan baxmaq. İki ayrı tətbiq bir-birindən ayrı
    düşür — nəticə ya deşik, ya da real istifadəçilərin kilidlənməsidir.
    Burada isə yoxlama əsl asılılıq ağacını oxuyur, onu təqlid etmir, və
    deploy-dan əvvəl işləyir (`scripts/ship.sh` testləri məcburi qılır).
"""

import pytest
from fastapi.routing import APIRoute

from app.main import app

# Mühafizə sayılan asılılıqlar. `require_capability(...)` daxilən
# `require_user`-dan asılıdır, ona görə ağacı gəzəndə o da tutulur.
GUARDS = frozenset({"require_user", "require_admin_key"})

# --------------------------------------------------------------------------
# AÇIQ MARŞRUTLAR — hər sətir şüurlu qərardır.
#
# Buraya bir şey əlavə etməzdən əvvəl tək sual: bu cavab KİMİSƏ aid ola
# bilərmi? Məqalə, sahə, aqreqat statistika — yox, onlar korpus haqqındadır.
# Sual mətni, xəta logu, sənəd, kitabxana — bəli, onlar insana aiddir.
# --------------------------------------------------------------------------
PUBLIC: frozenset[tuple[str, str]] = frozenset({
    # Korpus: açıq elmi ədəbiyyat, məhsulun vitrini
    ("GET", "/api/search"),
    ("GET", "/api/papers"),
    ("GET", "/api/papers/featured"),
    ("GET", "/api/papers/{paper_id}/insights"),
    ("GET", "/api/papers/{paper_id}/relations"),
    ("GET", "/api/fields"),
    ("GET", "/api/landscape"),
    ("GET", "/api/cross-disciplinary"),

    # Aqreqat — heç bir fərdi sətir qaytarmır
    ("GET", "/api/analytics/summary"),
    ("GET", "/api/analytics/trends"),
    ("GET", "/api/analytics/trend-classes"),
    ("GET", "/api/analytics/top-authors"),

    # Redaksiya məzmunu
    ("GET", "/api/digests/latest"),

    # Giriş qapısı açıq olmalıdır; sürət limiti ilə qorunur
    ("POST", "/api/auth/register"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/logout"),
    ("GET", "/api/auth/plans"),

    # Paddle çağırır — sessiya YOXDUR, mühafizə HMAC imzasıdır (§ödəniş)
    ("POST", "/api/billing/webhook"),

    # Caddy və monitorinq üçün. Yalnız {"status": "ok"} qaytarır;
    # detallı variant `/health/services` admin arxasındadır.
    ("GET", "/health"),
})


def _routes() -> list[tuple[str, str, set[str]]]:
    """(metod, yol, asılılıq adları) — asılılıq ağacı rekursiv gəzilir."""
    def names(dep) -> set[str]:
        out = {getattr(dep.call, "__name__", "")} if dep.call else set()
        for sub in dep.dependencies:
            out |= names(sub)
        return out

    rows = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        deps = names(route.dependant)
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            rows.append((method, route.path, deps))
    return rows


@pytest.mark.parametrize("method,path,deps", _routes(), ids=lambda v: v if isinstance(v, str) else "")
def test_route_is_public_on_purpose_or_guarded(method, path, deps):
    """Standart rədd: siyahıda yoxdursa, mühafizə daşımalıdır."""
    if (method, path) in PUBLIC:
        return
    assert deps & GUARDS, (
        f"{method} {path} nə açıq siyahıdadır, nə də mühafizə daşıyır.\n"
        f"  Ya `dependencies=[Depends(require_user)]` (yaxud require_admin_key) əlavə et,\n"
        f"  ya da HƏQİQƏTƏN hamıya açıq olmalıdırsa, bu faylda PUBLIC siyahısına yaz\n"
        f"  və səbəbini yanına qeyd et."
    )


def test_public_list_has_no_stale_entries():
    """Siyahıdakı marşrut silinibsə, sətir də getməlidir.

    Ölü sətir siyahını yalançı edir: növbəti dəfə oxuyan adam olmayan
    endpoint-in açıq olduğunu düşünür və siyahıya güvənməyi dayandırır.
    """
    live = {(m, p) for m, p, _ in _routes()}
    stale = sorted(PUBLIC - live)
    assert not stale, f"PUBLIC siyahısında artıq mövcud olmayan marşrutlar: {stale}"


def test_personal_data_routes_are_never_public():
    """Şəxsi məlumat daşıyan yolların heç biri açıq siyahıya düşməməlidir.

    Bu, birincinin təkrarı deyil: yuxarıdakı test «mühafizə varmı» deyə
    soruşur, bu isə «kimsə bunu səhvən PUBLIC siyahısına yazıbmı» deyə.
    Siyahıya bir sətir əlavə etmək bir dəqiqəlik işdir — bu test həmin
    dəqiqədə dayandırır.
    """
    PERSONAL = ("/api/library", "/api/documents", "/api/logs", "/api/billing/usage",
                "/api/billing/checkout", "/api/auth/me", "/health/services")
    leaked = sorted(
        (m, p) for (m, p) in PUBLIC
        if any(p.startswith(pref) for pref in PERSONAL)
    )
    assert not leaked, f"Şəxsi məlumat yolu açıq siyahıdadır: {leaked}"
