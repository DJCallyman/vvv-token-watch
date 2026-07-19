"""Shared SlowAPI limiter instance.

Kept in its own module so route files can decorate endpoints without
circular imports through backend.main.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
