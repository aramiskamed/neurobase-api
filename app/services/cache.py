import json
from typing import Optional
from app.core.config import get_settings

settings = get_settings()


def _redis_factory():
    try:
        from upstash_redis import Redis
        return Redis(
            url=settings.UPSTASH_REDIS_REST_URL,
            token=settings.UPSTASH_REDIS_REST_TOKEN,
        )
    except ImportError:
        return None


_redis_client = None


def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = _redis_factory()
    return _redis_client


def cache_get(key: str) -> Optional[str]:
    r = get_redis()
    if not r:
        return None
    try:
        return r.get(key)
    except Exception:
        return None


def cache_set(key: str, value: str, ttl: int = 3600):
    r = get_redis()
    if not r:
        return
    try:
        r.setex(key, ttl, value)
    except Exception:
        pass


def cache_delete_pattern(pattern: str):
    r = get_redis()
    if not r:
        return
    try:
        keys = r.keys(pattern)
        if keys:
            r.delete(*keys)
    except Exception:
        pass


def rate_limit(user_id: str, limit: int = 50, window: int = 60) -> bool:
    """Returns True if allowed, False if rate limited."""
    r = get_redis()
    if not r:
        return True  # Allow if Redis unavailable
    
    key = f"ratelimit:{user_id}"
    try:
        current = r.get(key)
        if current is None:
            r.setex(key, window, "1")
            return True
        elif int(current) < limit:
            r.incr(key)
            return True
        else:
            return False
    except Exception:
        return True  # Allow on error
