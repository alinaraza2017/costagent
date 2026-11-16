"""Shared rate limiter for authentication and sensitive routes."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Header injection is disabled because SlowAPI expects a raw Response object,
# while these routes return validated Pydantic models. Limits are still enforced.
limiter = Limiter(key_func=get_remote_address, headers_enabled=False)
