from __future__ import annotations

import enum


class ConfigVars:
    ENABLED = "RATELIMIT_ENABLED"
    KEY_FUNC = "RATELIMIT_KEY_FUNC"
    KEY_PREFIX = "RATELIMIT_KEY_PREFIX"
    FAIL_ON_FIRST_BREACH = "RATELIMIT_FAIL_ON_FIRST_BREACH"
    ON_BREACH = "RATELIMIT_ON_BREACH_CALLBACK"
    SWALLOW_ERRORS = "RATELIMIT_SWALLOW_ERRORS"
    APPLICATION_LIMITS = "RATELIMIT_APPLICATION"
    APPLICATION_LIMITS_COST = "RATELIMIT_APPLICATION_COST"
    DEFAULT_LIMITS = "RATELIMIT_DEFAULT"
    DEFAULT_LIMITS_PER_METHOD = "RATELIMIT_DEFAULTS_PER_METHOD"
    DEFAULT_LIMITS_EXEMPT_WHEN = "RATELIMIT_DEFAULTS_EXEMPT_WHEN"
    DEFAULT_LIMITS_DEDUCT_WHEN = "RATELIMIT_DEFAULTS_DEDUCT_WHEN"
    DEFAULT_LIMITS_COST = "RATELIMIT_DEFAULTS_COST"
    STRATEGY = "RATELIMIT_STRATEGY"
    STORAGE_URI = "RATELIMIT_STORAGE_URI"
    STORAGE_URL = "RATELIMIT_STORAGE_URL"  # Deprecated due to inconsistency.
    STORAGE_OPTIONS = "RATELIMIT_STORAGE_OPTIONS"
    HEADERS_ENABLED = "RATELIMIT_HEADERS_ENABLED"
    HEADER_LIMIT = "RATELIMIT_HEADER_LIMIT"
    HEADER_REMAINING = "RATELIMIT_HEADER_REMAINING"
    HEADER_RESET = "RATELIMIT_HEADER_RESET"
    HEADER_RETRY_AFTER = "RATELIMIT_HEADER_RETRY_AFTER"
    HEADER_RETRY_AFTER_VALUE = "RATELIMIT_HEADER_RETRY_AFTER_VALUE"
    IN_MEMORY_FALLBACK = "RATELIMIT_IN_MEMORY_FALLBACK"
    IN_MEMORY_FALLBACK_ENABLED = "RATELIMIT_IN_MEMORY_FALLBACK_ENABLED"


class HeaderNames(enum.Enum):
    """
    Enumeration of supported rate limit related headers to
    be used when configuring via :paramref:`~flask_limiter.Limiter.header_name_mapping`
    """

    #: Timestamp at which this rate limit will be reset
    RESET = "X-RateLimit-Reset"
    #: Remaining number of requests within the current window
    REMAINING = "X-RateLimit-Remaining"
    #: Total number of allowed requests within a window
    LIMIT = "X-RateLimit-Limit"
    #: Number of seconds to retry after at
    RETRY_AFTER = "Retry-After"


class ExemptionScope(enum.Flag):
    """
    Flags used to configure the scope of exemption when used
    in conjunction with :meth:`~flask_limiter.Limiter.exempt`.
    """

    NONE = 0

    #: Exempt from application wide "global" limits
    APPLICATION = enum.auto()
    #: Exempt from default limits configured on the extension
    DEFAULT = enum.auto()
    #: Exempts any nested blueprints. See :ref:`recipes:nested blueprints`
    DESCENDENTS = enum.auto()
    #: Exempt from any rate limits inherited from ancestor blueprints.
    #: See :ref:`recipes:nested blueprints`
    ANCESTORS = enum.auto()


MAX_BACKEND_CHECKS = 5
