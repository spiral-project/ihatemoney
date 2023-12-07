"""Flask-Limiter extension for rate limiting."""
from . import _version
from .constants import ExemptionScope, HeaderNames
from .errors import RateLimitExceeded
from .extension import Limiter
from .wrappers import RequestLimit

__all__ = [
    "ExemptionScope",
    "HeaderNames",
    "Limiter",
    "RateLimitExceeded",
    "RequestLimit",
]

#: Aliased for backward compatibility
HEADERS = HeaderNames

__version__ = _version.get_versions()["version"]  # type: ignore
