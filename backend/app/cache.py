import json
from collections.abc import Callable

import redis

from .config import settings

_r = redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=3)


def get_json(key: str):
    try:
        raw = _r.get(key)
        return json.loads(raw) if raw else None
    except redis.RedisError:
        return None


def set_json(key: str, value, ttl: int) -> None:
    try:
        _r.set(key, json.dumps(value, default=str), ex=ttl)
    except redis.RedisError:
        pass


def get_or_set(key: str, ttl: int, producer: Callable[[], object]):
    """(dəyər, keşdən gəldimi) qaytarır. Redis əlçatan deyilsə, sadəcə producer işləyir."""
    cached = get_json(key)
    if cached is not None:
        return cached, True
    value = producer()
    set_json(key, value, ttl)
    return value, False


def ping() -> bool:
    """Redis-in həqiqətən əlçatan olduğunu yoxlayır (sistem statusu üçün)."""
    try:
        return bool(_r.ping())
    except redis.RedisError:
        return False


def invalidate(pattern: str) -> int:
    """Pattern-ə uyğun açarları silir (məs. ingest-dən sonra 'analytics:*')."""
    try:
        deleted = 0
        for key in _r.scan_iter(pattern):
            _r.delete(key)
            deleted += 1
        return deleted
    except redis.RedisError:
        return 0
