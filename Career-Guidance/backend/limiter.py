"""
CareerCompass AI — Rate Limiting Configuration
Uses SlowAPI with remote IP address key function (unauthenticated).
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_rate_limit_key(request: Request) -> str:
    """
    Returns client IP address for rate limiting.
    """
    return get_remote_address(request)


limiter = Limiter(key_func=get_rate_limit_key)
