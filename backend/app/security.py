"""İctimai deploy üçün qoruma qatı.

İki ayrı problem həll olunur:
  1. YAZMA endpoint-ləri (ingest, digest, error log) açıq qalsa istənilən adam
     bazaya məqalə yaza bilər  ->  admin açarı tələb olunur.
  2. /api/ask hər çağırışda Groq kvotasını xərcləyir  ->  IP üzrə limit və
     günlük ümumi tavan.

Limitlər Redis-də saxlanılır. Redis əlçatmaz olsa limit yoxlaması ötürülür
(app onsuz da keşsiz işləyə bilir), amma yazma qorunması Redis-dən asılı
deyil — o, sırf açar yoxlamasıdır.
"""

from datetime import datetime, timezone

from fastapi import Header, HTTPException, Request

from .cache import _r
from .config import settings


def client_ip(request: Request) -> str:
    """Reverse proxy arxasında real IP.

    X-Forwarded-For yalnız TRUST_PROXY aktivdirsə oxunur — əks halda
    istənilən istifadəçi başlığı saxtalaşdırıb limiti keçə bilər.
    """
    if settings.trust_proxy:
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def require_admin_key(x_api_key: str | None = Header(default=None)) -> None:
    """Yazma əməliyyatları üçün. PUBLIC_MODE sönülüdürsə (lokal iş) sərbəstdir."""
    if not settings.public_mode:
        return
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=503,
            detail="Server ictimai rejimdədir, amma ADMIN_API_KEY təyin olunmayıb.",
        )
    if x_api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Yanlış və ya çatışmayan X-API-Key.")


def _hit(key: str, limit: int, ttl: int) -> tuple[bool, int]:
    """Sayğacı artırır. (icazə_var, qalan) qaytarır. Redis yoxdursa icazə verilir."""
    try:
        used = _r.incr(key)
        if used == 1:
            _r.expire(key, ttl)
        return used <= limit, max(0, limit - used)
    except Exception:
        return True, limit


def enforce_ask_limits(request: Request) -> None:
    """Bahalı LLM endpoint-i: IP üzrə saatlıq limit + günlük ümumi tavan."""
    if not settings.public_mode:
        return

    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    ok_global, left = _hit(f"rl:ask:global:{day}", settings.ask_daily_budget, 86400)
    if not ok_global:
        raise HTTPException(
            status_code=429,
            detail="Bu günün ümumi sual limiti doldu. Sabah yenidən cəhd et.",
            headers={"Retry-After": "3600"},
        )

    ip = client_ip(request)
    ok_ip, remaining = _hit(f"rl:ask:{ip}", settings.ask_rate_limit, 3600)
    if not ok_ip:
        raise HTTPException(
            status_code=429,
            detail=f"Saatlıq sual limiti doldu ({settings.ask_rate_limit}/saat). Bir azdan yenidən cəhd et.",
            headers={"Retry-After": "600"},
        )


def enforce_search_limits(request: Request) -> None:
    """Axtarış ucuzdur (LLM yoxdur) — yalnız sui-istifadəyə qarşı geniş limit."""
    if not settings.public_mode:
        return
    ip = client_ip(request)
    ok, _ = _hit(f"rl:search:{ip}", settings.search_rate_limit, 3600)
    if not ok:
        raise HTTPException(
            status_code=429,
            detail=f"Saatlıq axtarış limiti doldu ({settings.search_rate_limit}/saat).",
            headers={"Retry-After": "600"},
        )
