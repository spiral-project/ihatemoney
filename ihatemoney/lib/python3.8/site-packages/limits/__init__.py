"""
Rate limiting with commonly used storage backends
"""

from . import _version, aio, storage, strategies
from .limits import (
    RateLimitItem,
    RateLimitItemPerDay,
    RateLimitItemPerHour,
    RateLimitItemPerMinute,
    RateLimitItemPerMonth,
    RateLimitItemPerSecond,
    RateLimitItemPerYear,
)
from .util import WindowStats, parse, parse_many

__all__ = [
    "RateLimitItem",
    "RateLimitItemPerYear",
    "RateLimitItemPerMonth",
    "RateLimitItemPerDay",
    "RateLimitItemPerHour",
    "RateLimitItemPerMinute",
    "RateLimitItemPerSecond",
    "aio",
    "storage",
    "strategies",
    "parse",
    "parse_many",
    "WindowStats",
]

__version__ = _version.get_versions()["version"]  # type: ignore
