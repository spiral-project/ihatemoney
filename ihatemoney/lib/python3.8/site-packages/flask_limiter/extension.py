from __future__ import annotations

import dataclasses
import traceback
import warnings
from types import TracebackType

from ordered_set import OrderedSet

from .util import get_qualified_name

"""
Flask-Limiter Extension
"""
import datetime
import itertools
import logging
import time
import weakref
from collections import defaultdict
from functools import partial, wraps
from typing import Type, overload

import flask
import flask.wrappers
from limits.errors import ConfigurationError
from limits.storage import MemoryStorage, Storage, storage_from_string
from limits.strategies import STRATEGIES, RateLimiter
from werkzeug.http import http_date, parse_date

from ._compat import request_context
from .constants import MAX_BACKEND_CHECKS, ConfigVars, ExemptionScope, HeaderNames
from .errors import RateLimitExceeded
from .manager import LimitManager
from .typing import (
    Callable,
    Dict,
    List,
    Optional,
    P,
    R,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
)
from .wrappers import Limit, LimitGroup, RequestLimit


@dataclasses.dataclass
class LimiterContext:
    rate_limiting_complete: dict[str, bool] = dataclasses.field(default_factory=dict)
    view_rate_limit: Optional[RequestLimit] = None
    view_rate_limits: List[RequestLimit] = dataclasses.field(default_factory=list)
    conditional_deductions: Dict[Limit, List[str]] = dataclasses.field(
        default_factory=dict
    )
    seen_limits: OrderedSet[Limit] = dataclasses.field(default_factory=OrderedSet)

    def reset(self) -> None:
        self.rate_limiting_complete.clear()
        self.view_rate_limit = None
        self.view_rate_limits.clear()
        self.conditional_deductions.clear()


class Limiter:
    """
    The :class:`Limiter` class initializes the Flask-Limiter extension.

    :param app: :class:`flask.Flask` instance to initialize the extension with.
    :param key_func: a callable that returns the domain to rate limit
      by.
    :param default_limits: a variable list of strings or callables
     returning strings denoting default limits to apply to all routes.
     :ref:`ratelimit-string` for  more details.
    :param default_limits_per_method: whether default limits are applied
     per method, per route or as a combination of all method per route.
    :param default_limits_exempt_when: a function that should return
     True/False to decide if the default limits should be skipped
    :param default_limits_deduct_when: a function that receives the
     current :class:`flask.Response` object and returns True/False to decide
     if a deduction should be made from the default rate limit(s)
    :param default_limits_cost: The cost of a hit to the default limits as an
     integer or a function that takes no parameters and returns an integer
     (Default: ``1``).
    :param application_limits: a variable list of strings or callables
     returning strings for limits that are applied to the entire application
     (i.e a shared limit for all routes)
    :param application_limits_cost: The cost of a hit to the global application
     limits as an integer or a function that takes no parameters and returns an
     integer (Default: ``1``).
    :param headers_enabled: whether ``X-RateLimit`` response headers are
     written.
    :param header_name_mapping: Mapping of header names to use if
     :paramref:`Limiter.headers_enabled` is ``True``. If no mapping is provided
     the default values will be used.
    :param strategy: the strategy to use. Refer to :ref:`ratelimit-strategy`
    :param storage_uri: the storage location.
     Refer to :data:`RATELIMIT_STORAGE_URI`
    :param storage_options: kwargs to pass to the storage implementation
     upon instantiation.
    :param auto_check: whether to automatically check the rate limit in
     the before_request chain of the application. default ``True``
    :param swallow_errors: whether to swallow any errors when hitting a rate
     limit. An exception will still be logged. default ``False``
    :param fail_on_first_breach: whether to stop processing remaining limits
     after the first breach. default ``True``
    :param on_breach: a function that will be called when any limit in this
     extension is breached. If the function returns an instance of :class:`flask.Response`
     that will be the response embedded into the :exc:`RateLimitExceeded` exception
     raised.
    :param in_memory_fallback: a variable list of strings or callables
     returning strings denoting fallback limits to apply when the storage is
     down.
    :param in_memory_fallback_enabled: fall back to in memory
     storage when the main storage is down and inherits the original limits.
     default ``False``
    :param retry_after: Allows configuration of how the value of the
     `Retry-After` header is rendered. One of `http-date` or `delta-seconds`.
    :param key_prefix: prefix prepended to rate limiter keys and app context global names.
    :param enabled: Whether the extension is enabled or not
    """

    def __init__(
        self,
        app: Optional[flask.Flask] = None,
        key_func: Optional[Callable[[], str]] = None,
        default_limits: Optional[List[Union[str, Callable[[], str]]]] = None,
        default_limits_per_method: Optional[bool] = None,
        default_limits_exempt_when: Optional[Callable[[], bool]] = None,
        default_limits_deduct_when: Optional[
            Callable[[flask.wrappers.Response], bool]
        ] = None,
        default_limits_cost: Optional[Union[int, Callable[[], int]]] = None,
        application_limits: Optional[List[Union[str, Callable[[], str]]]] = None,
        application_limits_cost: Optional[Union[int, Callable[[], int]]] = None,
        headers_enabled: Optional[bool] = None,
        header_name_mapping: Optional[Dict[HeaderNames, str]] = None,
        strategy: Optional[str] = None,
        storage_uri: Optional[str] = None,
        storage_options: Optional[Dict[str, Union[str, int]]] = None,
        auto_check: bool = True,
        swallow_errors: Optional[bool] = None,
        fail_on_first_breach: Optional[bool] = None,
        on_breach: Optional[
            Callable[[RequestLimit], Optional[flask.wrappers.Response]]
        ] = None,
        in_memory_fallback: Optional[List[str]] = None,
        in_memory_fallback_enabled: Optional[bool] = None,
        retry_after: Optional[str] = None,
        key_prefix: str = "",
        enabled: bool = True,
    ) -> None:
        self.app = app
        self.logger = logging.getLogger("flask-limiter")

        self.enabled = enabled
        self.initialized = False
        self._default_limits_per_method = default_limits_per_method
        self._default_limits_exempt_when = default_limits_exempt_when
        self._default_limits_deduct_when = default_limits_deduct_when
        self._default_limits_cost = default_limits_cost
        self._application_limits_cost = application_limits_cost
        self._in_memory_fallback = []
        self._in_memory_fallback_enabled = in_memory_fallback_enabled or (
            in_memory_fallback and len(in_memory_fallback) > 0
        )
        self._route_exemptions: Dict[str, ExemptionScope] = defaultdict(
            lambda: ExemptionScope.NONE
        )
        self._blueprint_exemptions: Dict[str, ExemptionScope] = defaultdict(
            lambda: ExemptionScope.NONE
        )
        self._request_filters: List[Callable[[], bool]] = []

        self._headers_enabled = headers_enabled
        self._header_mapping = header_name_mapping or {}
        self._retry_after = retry_after
        self._strategy = strategy
        self._storage_uri = storage_uri
        self._storage_options = storage_options or {}
        self._auto_check = auto_check
        self._swallow_errors = swallow_errors
        self._fail_on_first_breach = fail_on_first_breach
        self._on_breach = on_breach
        # No longer optional
        assert key_func

        self._key_func = key_func
        self._key_prefix = key_prefix

        _default_limits = (
            [
                LimitGroup(
                    limit_provider=limit,
                    key_function=self._key_func,
                )
                for limit in default_limits
            ]
            if default_limits
            else []
        )

        _application_limits = (
            [
                LimitGroup(
                    limit_provider=limit,
                    key_function=self._key_func,
                    scope="global",
                )
                for limit in application_limits
            ]
            if application_limits
            else []
        )

        if in_memory_fallback:
            for limit in in_memory_fallback:
                self._in_memory_fallback.append(
                    LimitGroup(
                        limit_provider=limit,
                        key_function=self._key_func,
                    )
                )

        self._storage: Optional[Storage] = None
        self._limiter: Optional[RateLimiter] = None
        self._storage_dead = False
        self._fallback_limiter: Optional[RateLimiter] = None

        self.__check_backend_count = 0
        self.__last_check_backend = time.time()
        self._marked_for_limiting: Set[str] = set()

        self.logger.addHandler(logging.NullHandler())

        self.limit_manager = LimitManager(
            application_limits=_application_limits,
            default_limits=_default_limits,
            static_decorated_limits={},
            dynamic_decorated_limits={},
            static_blueprint_limits={},
            dynamic_blueprint_limits={},
            route_exemptions=self._route_exemptions,
            blueprint_exemptions=self._blueprint_exemptions,
        )

        if app:
            self.init_app(app)

    def init_app(self, app: flask.Flask) -> None:
        """
        :param app: :class:`flask.Flask` instance to rate limit.
        """
        config = app.config
        self.enabled = config.setdefault(ConfigVars.ENABLED, self.enabled)

        if not self.enabled:
            return

        if self._default_limits_per_method is None:
            self._default_limits_per_method = bool(
                config.get(ConfigVars.DEFAULT_LIMITS_PER_METHOD, False)
            )
        self._default_limits_exempt_when = (
            self._default_limits_exempt_when
            or config.get(ConfigVars.DEFAULT_LIMITS_EXEMPT_WHEN)
        )
        self._default_limits_deduct_when = (
            self._default_limits_deduct_when
            or config.get(ConfigVars.DEFAULT_LIMITS_DEDUCT_WHEN)
        )
        self._default_limits_cost = self._default_limits_cost or config.get(
            ConfigVars.DEFAULT_LIMITS_COST, 1
        )

        if self._swallow_errors is None:
            self._swallow_errors = bool(config.get(ConfigVars.SWALLOW_ERRORS, False))

        if self._fail_on_first_breach is None:
            self._fail_on_first_breach = bool(
                config.get(ConfigVars.FAIL_ON_FIRST_BREACH, True)
            )

        if self._headers_enabled is None:
            self._headers_enabled = bool(config.get(ConfigVars.HEADERS_ENABLED, False))

        self._storage_options.update(config.get(ConfigVars.STORAGE_OPTIONS, {}))
        storage_uri_from_config = config.get(
            ConfigVars.STORAGE_URI, config.get(ConfigVars.STORAGE_URL, None)
        )
        if not storage_uri_from_config:
            if not self._storage_uri:
                warnings.warn(
                    "Using the in-memory storage for tracking rate limits as no storage "
                    "was explicitly specified. This is not recommended for production use. "
                    "See: https://flask-limiter.readthedocs.io#configuring-a-storage-backend "
                    "for documentation about configuring the storage backend."
                )
            storage_uri_from_config = "memory://"
        self._storage = cast(
            Storage,
            storage_from_string(
                self._storage_uri or storage_uri_from_config, **self._storage_options
            ),
        )
        self._strategy = self._strategy or config.setdefault(
            ConfigVars.STRATEGY, "fixed-window"
        )

        if self._strategy not in STRATEGIES:
            raise ConfigurationError(
                "Invalid rate limiting strategy %s" % self._strategy
            )
        self._limiter = STRATEGIES[self._strategy](self._storage)

        self._header_mapping = {
            HeaderNames.RESET: self._header_mapping.get(
                HeaderNames.RESET,
                config.get(ConfigVars.HEADER_RESET, HeaderNames.RESET.value),
            ),
            HeaderNames.REMAINING: self._header_mapping.get(
                HeaderNames.REMAINING,
                config.get(ConfigVars.HEADER_REMAINING, HeaderNames.REMAINING.value),
            ),
            HeaderNames.LIMIT: self._header_mapping.get(
                HeaderNames.LIMIT,
                config.get(ConfigVars.HEADER_LIMIT, HeaderNames.LIMIT.value),
            ),
            HeaderNames.RETRY_AFTER: self._header_mapping.get(
                HeaderNames.RETRY_AFTER,
                config.get(
                    ConfigVars.HEADER_RETRY_AFTER, HeaderNames.RETRY_AFTER.value
                ),
            ),
        }
        self._retry_after = self._retry_after or config.get(
            ConfigVars.HEADER_RETRY_AFTER_VALUE
        )

        self._key_prefix = self._key_prefix or config.get(ConfigVars.KEY_PREFIX, "")

        app_limits = config.get(ConfigVars.APPLICATION_LIMITS, None)
        self._application_limits_cost = self._application_limits_cost or config.get(
            ConfigVars.APPLICATION_LIMITS_COST, 1
        )

        if not self.limit_manager._application_limits and app_limits:
            self.limit_manager.set_application_limits(
                [
                    LimitGroup(
                        limit_provider=app_limits,
                        key_function=self._key_func,
                        scope="global",
                        cost=self._application_limits_cost,
                    )
                ]
            )
        else:
            app_limits = self.limit_manager._application_limits
            for group in app_limits:
                group.cost = self._application_limits_cost
            self.limit_manager.set_application_limits(app_limits)

        conf_limits = config.get(ConfigVars.DEFAULT_LIMITS, None)

        if not self.limit_manager._default_limits and conf_limits:
            self.limit_manager.set_default_limits(
                [
                    LimitGroup(
                        limit_provider=conf_limits,
                        key_function=self._key_func,
                        per_method=self._default_limits_per_method,
                        exempt_when=self._default_limits_exempt_when,
                        deduct_when=self._default_limits_deduct_when,
                        cost=self._default_limits_cost,
                    )
                ]
            )
        else:
            default_limit_groups = self.limit_manager._default_limits
            for group in default_limit_groups:
                group.per_method = self._default_limits_per_method
                group.exempt_when = self._default_limits_exempt_when
                group.deduct_when = self._default_limits_deduct_when
                group.cost = self._default_limits_cost
            self.limit_manager.set_default_limits(default_limit_groups)
        self.__configure_fallbacks(app, self._strategy)

        # purely for backward compatibility as stated in flask documentation
        if not hasattr(app, "extensions"):
            app.extensions = {}  # pragma: no cover

        if self not in app.extensions.setdefault("limiter", set()):
            if self._auto_check:
                app.before_request(self._check_request_limit)

            app.after_request(partial(Limiter.__inject_headers, self))
            app.teardown_request(self.__release_context)
        app.extensions["limiter"].add(self)
        self.initialized = True

    @property
    def context(self) -> LimiterContext:
        ctx = request_context()
        if not hasattr(ctx, "_limiter_request_context"):
            ctx._limiter_request_context = defaultdict(LimiterContext)  # type: ignore
        return cast(
            Dict[str, LimiterContext],
            ctx._limiter_request_context,  # type: ignore
        )[self._key_prefix]

    def limit(
        self,
        limit_value: Union[str, Callable[[], str]],
        key_func: Optional[Callable[[], str]] = None,
        per_method: bool = False,
        methods: Optional[List[str]] = None,
        error_message: Optional[str] = None,
        exempt_when: Optional[Callable[[], bool]] = None,
        override_defaults: bool = True,
        deduct_when: Optional[Callable[[flask.wrappers.Response], bool]] = None,
        on_breach: Optional[
            Callable[[RequestLimit], Optional[flask.wrappers.Response]]
        ] = None,
        cost: Union[int, Callable[[], int]] = 1,
    ) -> LimitDecorator:
        """
        Decorator to be used for rate limiting individual routes or blueprints.

        :param limit_value: rate limit string or a callable that returns a
         string. :ref:`ratelimit-string` for more details.
        :param key_func: function/lambda to extract the unique
         identifier for the rate limit. defaults to remote address of the
         request.
        :param per_method: whether the limit is sub categorized into the
         http method of the request.
        :param methods: if specified, only the methods in this list will
         be rate limited (default: ``None``).
        :param error_message: string (or callable that returns one) to override
         the error message used in the response.
        :param exempt_when: function/lambda used to decide if the rate
         limit should skipped.
        :param override_defaults:  whether the decorated limit overrides
         the default limits (Default: ``True``).

         .. note:: When used with a :class:`~flask.Blueprint` the meaning
            of the parameter extends to any parents the blueprint instance is
            registered under. For more details see :ref:`recipes:nested blueprints`

        :param deduct_when: a function that receives the current
         :class:`flask.Response` object and returns True/False to decide if a
         deduction should be done from the rate limit
        :param on_breach: a function that will be called when this limit
         is breached. If the function returns an instance of :class:`flask.Response`
         that will be the response embedded into the :exc:`RateLimitExceeded` exception
         raised.
        :param cost: The cost of a hit or a function that
         takes no parameters and returns the cost as an integer (Default: ``1``).

        Changes
          - .. versionadded:: 2.9.0 The returned object can also be used as a context manager
            for rate limiting a code block inside a view. For example::

                @app.route("/")
                def route():
                   try:
                       with limiter.limit("10/second"):
                           # something expensive
                   except RateLimitExceeded: pass
        """

        return LimitDecorator(
            self,
            limit_value,
            key_func,
            per_method=per_method,
            methods=methods,
            error_message=error_message,
            exempt_when=exempt_when,
            override_defaults=override_defaults,
            deduct_when=deduct_when,
            on_breach=on_breach,
            cost=cost,
        )

    def shared_limit(
        self,
        limit_value: Union[str, Callable[[], str]],
        scope: Union[str, Callable[[str], str]],
        key_func: Optional[Callable[[], str]] = None,
        per_method: bool = False,
        methods: Optional[List[str]] = None,
        error_message: Optional[str] = None,
        exempt_when: Optional[Callable[[], bool]] = None,
        override_defaults: bool = True,
        deduct_when: Optional[Callable[[flask.wrappers.Response], bool]] = None,
        on_breach: Optional[
            Callable[[RequestLimit], Optional[flask.wrappers.Response]]
        ] = None,
        cost: Union[int, Callable[[], int]] = 1,
    ) -> LimitDecorator:
        """
        decorator to be applied to multiple routes sharing the same rate limit.

        :param limit_value: rate limit string or a callable that returns a
         string. :ref:`ratelimit-string` for more details.
        :param scope: a string or callable that returns a string
         for defining the rate limiting scope.
        :param key_func: function/lambda to extract the unique
         identifier for the rate limit. defaults to remote address of the
         request.
        :param per_method: whether the limit is sub categorized into the
         http method of the request.
        :param methods: if specified, only the methods in this list will
         be rate limited (default: ``None``).
        :param error_message: string (or callable that returns one) to override
         the error message used in the response.
        :param function exempt_when: function/lambda used to decide if the rate
         limit should skipped.
        :param override_defaults: whether the decorated limit overrides
         the default limits. (default: ``True``)

         .. note:: When used with a :class:`~flask.Blueprint` the meaning
            of the parameter extends to any parents the blueprint instance is
            registered under. For more details see :ref:`recipes:nested blueprints`
        :param deduct_when: a function that receives the current
         :class:`flask.Response`  object and returns True/False to decide if a
         deduction should be done from the rate limit
        :param on_breach: a function that will be called when this limit
         is breached. If the function returns an instance of :class:`flask.Response`
         that will be the response embedded into the :exc:`RateLimitExceeded` exception
         raised.
        :param cost: The cost of a hit or a function that
         takes no parameters and returns the cost as an integer (default: ``1``).
        """

        return LimitDecorator(
            self,
            limit_value,
            key_func,
            True,
            scope,
            per_method=per_method,
            methods=methods,
            error_message=error_message,
            exempt_when=exempt_when,
            override_defaults=override_defaults,
            deduct_when=deduct_when,
            on_breach=on_breach,
            cost=cost,
        )

    @overload
    def exempt(
        self,
        obj: flask.Blueprint,
        *,
        flags: ExemptionScope = ExemptionScope.APPLICATION | ExemptionScope.DEFAULT,
    ) -> flask.Blueprint:
        ...

    @overload
    def exempt(
        self,
        obj: Callable[..., R],
        *,
        flags: ExemptionScope = ExemptionScope.APPLICATION | ExemptionScope.DEFAULT,
    ) -> Callable[..., R]:
        ...

    @overload
    def exempt(
        self,
        *,
        flags: ExemptionScope = ExemptionScope.APPLICATION | ExemptionScope.DEFAULT,
    ) -> Union[
        Callable[[Callable[P, R]], Callable[P, R]],
        Callable[[flask.Blueprint], flask.Blueprint],
    ]:
        ...

    def exempt(
        self,
        obj: Optional[Union[Callable[..., R], flask.Blueprint]] = None,
        *,
        flags: ExemptionScope = ExemptionScope.APPLICATION | ExemptionScope.DEFAULT,
    ) -> Union[
        Callable[..., R],
        flask.Blueprint,
        Callable[[Callable[P, R]], Callable[P, R]],
        Callable[[flask.Blueprint], flask.Blueprint],
    ]:
        """
        Mark a view function or all views in a blueprint as exempt from
        rate limits.

        :param obj: view function or blueprint to mark as exempt.
        :param flags: Controls the scope of the exemption. By default
         application wide limits and defaults configured on the extension
         are opted out of. Additional flags can be used to control the behavior
         when :paramref:`obj` is a Blueprint that is nested under another Blueprint
         or has other Blueprints nested under it (See :ref:`recipes:nested blueprints`)

        The method can be used either as a decorator without any arguments (the default
        flags will apply and the route will be exempt from default and application limits::

            @app.route("...")
            @limiter.exempt
            def route(...):
               ...

        Specific exemption flags can be provided at decoration time::

            @app.route("...")
            @limiter.exempt(flags=ExemptionScope.APPLICATION)
            def route(...):
                ...

        If an entire blueprint (i.e. all routes under it) are to be exempted the method
        can be called with the blueprint as the first parameter and any additional flags::

            bp = Blueprint(...)
            limiter.exempt(bp)
            limiter.exempt(
                bp,
                flags=ExemptionScope.DEFAULT|ExemptionScope.APPLICATION|ExemptionScope.ANCESTORS
            )

        """

        if isinstance(obj, flask.Blueprint):
            self.limit_manager.add_blueprint_exemption(obj.name, flags)
        elif obj:
            self.limit_manager.add_route_exemption(get_qualified_name(obj), flags)
        else:
            _R = TypeVar("_R")
            _WO = TypeVar("_WO", Callable[..., _R], flask.Blueprint)

            def wrapper(obj: _WO) -> _WO:
                return self.exempt(obj, flags=flags)

            return wrapper
        return obj

    def request_filter(self, fn: Callable[[], bool]) -> Callable[[], bool]:
        """
        decorator to mark a function as a filter to be executed
        to check if the request is exempt from rate limiting.

        :param fn: The function will be called before evaluating any rate limits
         to decide whether to perform rate limit or skip it.
        """
        self._request_filters.append(fn)

        return fn

    def __configure_fallbacks(self, app: flask.Flask, strategy: str) -> None:
        config = app.config
        fallback_enabled = config.get(ConfigVars.IN_MEMORY_FALLBACK_ENABLED, False)
        fallback_limits = config.get(ConfigVars.IN_MEMORY_FALLBACK, None)

        if not self._in_memory_fallback and fallback_limits:
            self._in_memory_fallback = [
                LimitGroup(
                    limit_provider=fallback_limits,
                    key_function=self._key_func,
                    scope=None,
                    per_method=False,
                    cost=1,
                )
            ]

        if not self._in_memory_fallback_enabled:
            self._in_memory_fallback_enabled = (
                fallback_enabled or len(self._in_memory_fallback) > 0
            )

        if self._in_memory_fallback_enabled:
            self._fallback_storage = MemoryStorage()
            self._fallback_limiter = STRATEGIES[strategy](self._fallback_storage)

    def __should_check_backend(self) -> bool:
        if self.__check_backend_count > MAX_BACKEND_CHECKS:
            self.__check_backend_count = 0

        if time.time() - self.__last_check_backend > pow(2, self.__check_backend_count):
            self.__last_check_backend = time.time()
            self.__check_backend_count += 1

            return True

        return False

    def check(self) -> None:
        """
        Explicitly check the limits for the current request. This is only relevant
        if the extension was initialized with :paramref:`~flask_limiter.Limiter.auto_check`
        set to ``False``


        :raises: RateLimitExceeded
        """
        self._check_request_limit(in_middleware=False)

    def reset(self) -> None:
        """
        resets the storage if it supports being reset
        """
        try:
            self.storage.reset()
            self.logger.info("Storage has been reset and all limits cleared")
        except NotImplementedError:
            self.logger.warning("This storage type does not support being reset")

    @property
    def storage(self) -> Storage:
        """
        The backend storage configured for the rate limiter
        """
        assert self._storage
        return self._storage

    @property
    def limiter(self) -> RateLimiter:
        """
        Instance of the rate limiting strategy used for performing
        rate limiting.
        """
        if self._storage_dead and self._in_memory_fallback_enabled:
            limiter = self._fallback_limiter
        else:
            limiter = self._limiter
        assert limiter
        return limiter

    @property
    def current_limit(self) -> Optional[RequestLimit]:
        """
        Get details for the most relevant rate limit used in this request.

        In a scenario where multiple rate limits are active for a single request
        and none are breached, the rate limit which applies to the smallest
        time window will be returned.

        .. important:: The value of ``remaining`` in :class:`RequestLimit` is after
           deduction for the current request.


        For example::

            @limit("1/second")
            @limit("60/minute")
            @limit("2/day")
            def route(...):
                ...

        - Request 1 at ``t=0`` (no breach): this will return the details for for ``1/second``
        - Request 2 at ``t=1`` (no breach): it will still return the details for ``1/second``
        - Request 3 at ``t=2`` (breach): it will return the details for ``2/day``
        """
        return self.context.view_rate_limit

    @property
    def current_limits(self) -> List[RequestLimit]:
        """
        Get a list of all rate limits that were applicable and evaluated
        within the context of this request.

        The limits are returned in a sorted order by smallest window size first.
        """

        return self.context.view_rate_limits

    def __check_conditional_deductions(self, response: flask.wrappers.Response) -> None:
        for lim, args in self.context.conditional_deductions.items():
            if lim.deduct_when and lim.deduct_when(response):
                try:
                    self.limiter.hit(lim.limit, *args, cost=lim.cost)
                except Exception as err:
                    if self._swallow_errors:
                        self.logger.exception(
                            "Failed to deduct rate limit. " "Swallowing error"
                        )
                    else:
                        raise err

    def __inject_headers(
        self, response: flask.wrappers.Response
    ) -> flask.wrappers.Response:
        self.__check_conditional_deductions(response)
        header_limit = self.current_limit
        if (
            self.enabled
            and self._headers_enabled
            and header_limit
            and self._header_mapping
        ):
            try:
                reset_at = header_limit.reset_at
                response.headers.add(
                    self._header_mapping[HeaderNames.LIMIT],
                    str(header_limit.limit.amount),
                )
                response.headers.add(
                    self._header_mapping[HeaderNames.REMAINING], header_limit.remaining
                )
                response.headers.add(self._header_mapping[HeaderNames.RESET], reset_at)

                # response may have an existing retry after
                existing_retry_after_header = response.headers.get("Retry-After")

                if existing_retry_after_header is not None:
                    # might be in http-date format
                    retry_after: Optional[Union[float, datetime.datetime]] = parse_date(
                        existing_retry_after_header
                    )

                    # parse_date failure returns None

                    if retry_after is None:
                        retry_after = time.time() + int(existing_retry_after_header)

                    if isinstance(retry_after, datetime.datetime):
                        retry_after = time.mktime(retry_after.timetuple())

                    reset_at = max(int(retry_after), reset_at)

                # set the header instead of using add
                response.headers.set(
                    self._header_mapping[HeaderNames.RETRY_AFTER],
                    self._retry_after == "http-date"
                    and http_date(reset_at)
                    or int(reset_at - time.time()),
                )
            except Exception as e:  # noqa: E722
                if self._in_memory_fallback_enabled and not self._storage_dead:
                    self.logger.warning(
                        "Rate limit storage unreachable - falling back to"
                        " in-memory storage"
                    )
                    self._storage_dead = True
                    response = self.__inject_headers(response)
                else:
                    if self._swallow_errors:
                        self.logger.exception(
                            "Failed to update rate limit headers. " "Swallowing error"
                        )
                    else:
                        raise e

        return response

    def __check_all_limits_exempt(
        self, endpoint: Optional[str], callable_name: Optional[str] = None
    ) -> bool:
        return bool(
            not endpoint
            or not (self.enabled and self.initialized)
            or endpoint == "static"
            or any(fn() for fn in self._request_filters)
            or (
                self.context.rate_limiting_complete.get(callable_name, False)
                if callable_name
                else any(self.context.rate_limiting_complete.values())
            )
        )

    def __filter_limits(
        self,
        endpoint: Optional[str],
        blueprint: Optional[str],
        callable_name: Optional[str],
        in_middleware: bool = False,
    ) -> List[Limit]:

        if callable_name:
            name = callable_name
        else:
            view_func = flask.current_app.view_functions.get(endpoint or "", None)
            name = get_qualified_name(view_func) if view_func else ""

        if self.__check_all_limits_exempt(endpoint, callable_name):
            return []

        marked_for_limiting = (
            name in self._marked_for_limiting
            or self.limit_manager.has_hints(endpoint or "")
        )
        fallback_limits = []

        if self._storage_dead and self._fallback_limiter:
            if in_middleware and name in self._marked_for_limiting:
                pass
            else:
                if (
                    self.__should_check_backend()
                    and self._storage
                    and self._storage.check()
                ):
                    self.logger.info("Rate limit storage recovered")
                    self._storage_dead = False
                    self.__check_backend_count = 0
                else:
                    fallback_limits = list(itertools.chain(*self._in_memory_fallback))
        resolved_limits = self.limit_manager.resolve_limits(
            flask.current_app,
            endpoint,
            blueprint,
            name,
            in_middleware,
            marked_for_limiting,
            fallback_limits,
        )
        limits = OrderedSet(resolved_limits) - self.context.seen_limits
        self.context.seen_limits.update(limits)
        return list(limits)

    def __evaluate_limits(self, endpoint: str, limits: List[Limit]) -> None:
        failed_limits: List[Tuple[Limit, List[str]]] = []
        limit_for_header: Optional[RequestLimit] = None
        view_limits: List[RequestLimit] = []
        for lim in sorted(limits, key=lambda x: x.limit):
            limit_scope = lim.scope or endpoint

            if lim.is_exempt or lim.method_exempt:
                continue

            if lim.per_method:
                limit_scope += f":{flask.request.method}"
            limit_key = lim.key_func()
            args = [limit_key, limit_scope]
            kwargs = {}

            if not all(args):
                self.logger.error(
                    f"Skipping limit: {lim.limit}. Empty value found in parameters."
                )

                continue

            if self._key_prefix:
                args = [self._key_prefix, *args]

            if lim.deduct_when:
                self.context.conditional_deductions[lim] = args
                method = self.limiter.test
            else:
                method = self.limiter.hit
                kwargs["cost"] = lim.cost

            if not limit_for_header or lim.limit < limit_for_header.limit:
                limit_for_header = RequestLimit(self, lim.limit, args, False)

            view_limits.append(RequestLimit(self, lim.limit, args, False))

            if not method(lim.limit, *args, **kwargs):
                self.logger.info(
                    "ratelimit %s (%s) exceeded at endpoint: %s",
                    lim.limit,
                    limit_key,
                    limit_scope,
                )
                failed_limits.append((lim, args))
                view_limits[-1].breached = True
                limit_for_header = view_limits[-1]
                if self._fail_on_first_breach:
                    break

        self.context.view_rate_limit = limit_for_header or None
        self.context.view_rate_limits = view_limits

        on_breach_response = None
        for limit in failed_limits:
            request_limit = RequestLimit(self, limit[0].limit, limit[1], True)
            for cb in dict.fromkeys([self._on_breach, limit[0].on_breach]):
                if cb:
                    try:
                        cb_response = cb(request_limit)
                        if isinstance(cb_response, flask.wrappers.Response):
                            on_breach_response = cb_response
                    except Exception as err:  # noqa
                        if self._swallow_errors:
                            self.logger.exception(
                                "on_breach callback failed with error %s", err
                            )
                        else:
                            raise err
        if failed_limits:
            raise RateLimitExceeded(
                sorted(failed_limits, key=lambda x: x[0].limit)[0][0],
                response=on_breach_response,
            )

    def _check_request_limit(
        self, callable_name: Optional[str] = None, in_middleware: bool = True
    ) -> None:
        endpoint = flask.request.endpoint or ""
        try:
            all_limits = self.__filter_limits(
                flask.request.endpoint,
                flask.request.blueprint,
                callable_name,
                in_middleware,
            )
            self.__evaluate_limits(endpoint, all_limits)
        except Exception as e:
            if isinstance(e, RateLimitExceeded):
                raise e

            if self._in_memory_fallback_enabled and not self._storage_dead:
                self.logger.warning(
                    "Rate limit storage unreachable - falling back to"
                    " in-memory storage"
                )
                self._storage_dead = True
                self.context.seen_limits.clear()
                self._check_request_limit(
                    callable_name=callable_name, in_middleware=in_middleware
                )
            else:
                if self._swallow_errors:
                    self.logger.exception("Failed to rate limit. Swallowing error")
                else:
                    raise e

    def __release_context(self, _: Optional[BaseException] = None) -> None:
        if self.context:
            self.context.reset()


class LimitDecorator:
    """
    Wrapper used by :meth:`~flask_limiter.Limiter.limit`
    and :meth:`~flask_limiter.Limiter.shared_limit`
    when wrapping view functions or blueprints.
    """

    def __init__(
        self,
        limiter: Limiter,
        limit_value: Union[Callable[[], str], str],
        key_func: Optional[Callable[[], str]] = None,
        shared: bool = False,
        scope: Optional[Union[Callable[[str], str], str]] = None,
        per_method: bool = False,
        methods: Optional[Sequence[str]] = None,
        error_message: Optional[str] = None,
        exempt_when: Optional[Callable[[], bool]] = None,
        override_defaults: bool = True,
        deduct_when: Optional[Callable[[flask.wrappers.Response], bool]] = None,
        on_breach: Optional[
            Callable[[RequestLimit], Optional[flask.wrappers.Response]]
        ] = None,
        cost: Union[Callable[[], int], int] = 1,
    ):
        self.limiter: weakref.ProxyType[Limiter] = weakref.proxy(limiter)
        self.limit_value = limit_value
        self.key_func = key_func or self.limiter._key_func
        self.scope = scope if shared else None
        self.per_method = per_method
        self.methods = tuple(methods) if methods else None
        self.error_message = error_message
        self.exempt_when = exempt_when
        self.override_defaults = override_defaults
        self.deduct_when = deduct_when
        self.on_breach = on_breach
        self.cost = cost
        self.is_static = not callable(self.limit_value)

    @property
    def dynamic_limit(self) -> Optional[LimitGroup]:
        return LimitGroup(
            limit_provider=self.limit_value,
            key_function=self.key_func,
            scope=self.scope,
            per_method=self.per_method,
            methods=self.methods,
            error_message=self.error_message,
            exempt_when=self.exempt_when,
            override_defaults=self.override_defaults,
            deduct_when=self.deduct_when,
            on_breach=self.on_breach,
            cost=self.cost,
        )

    @property
    def static_limits(self) -> List[Limit]:
        return list(
            LimitGroup(
                limit_provider=self.limit_value,
                key_function=self.key_func,
                scope=self.scope,
                per_method=self.per_method,
                methods=self.methods,
                error_message=self.error_message,
                exempt_when=self.exempt_when,
                override_defaults=self.override_defaults,
                deduct_when=self.deduct_when,
                on_breach=self.on_breach,
                cost=self.cost,
            )
        )

    def __enter__(self) -> None:
        tb = traceback.extract_stack(limit=2)
        qualified_location = f"{tb[0].filename}:{tb[0].name}:{tb[0].lineno}"

        # TODO: if use as a context manager becomes interesting/valuable
        #  a less hacky approach than using the traceback and piggy backing
        #  on the limit manager's knowledge of decorated limits might be worth it.
        if not self.is_static:
            self.limiter.limit_manager.add_decorated_runtime_limit(
                qualified_location, self.dynamic_limit
            )
        else:
            self.limiter.limit_manager.add_decorated_static_limit(
                qualified_location, *self.static_limits
            )

        self.limiter.limit_manager.add_endpoint_hint(
            flask.request.endpoint, qualified_location
        )

        self.limiter._check_request_limit(
            in_middleware=False, callable_name=qualified_location
        )

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        ...

    @overload
    def __call__(self, obj: Callable[P, R]) -> Callable[P, R]:
        ...

    @overload
    def __call__(self, obj: flask.Blueprint) -> None:
        ...

    def __call__(
        self, obj: Union[Callable[P, R], flask.Blueprint]
    ) -> Optional[Callable[P, R]]:
        is_route = not isinstance(obj, flask.Blueprint)
        if isinstance(obj, flask.Blueprint):
            name = obj.name
        else:
            name = get_qualified_name(obj)
        dynamic_limit = self.dynamic_limit if not self.is_static else None
        static_limits = []
        if self.is_static:
            try:
                static_limits = self.static_limits
            except ValueError as e:
                self.limiter.logger.error(
                    "failed to configure %s %s (%s)",
                    "view function" if is_route else "blueprint",
                    name,
                    e,
                )

        if isinstance(obj, flask.Blueprint):
            if not self.is_static:
                self.limiter.limit_manager.add_runtime_blueprint_limits(
                    name, dynamic_limit
                )
            else:
                self.limiter.limit_manager.add_static_blueprint_limits(
                    name, *static_limits
                )
            return None
        else:
            self.limiter._marked_for_limiting.add(name)
            if not self.is_static:
                self.limiter.limit_manager.add_decorated_runtime_limit(
                    name, dynamic_limit
                )
            else:
                self.limiter.limit_manager.add_decorated_static_limit(
                    name, *static_limits
                )

            @wraps(obj)
            def __inner(*a: P.args, **k: P.kwargs) -> R:
                if (
                    self.limiter._auto_check
                    and not self.limiter.context.rate_limiting_complete.get(name, False)
                ):
                    if flask.request.endpoint:
                        view_func = flask.current_app.view_functions.get(
                            flask.request.endpoint, None
                        )
                        if view_func and not get_qualified_name(view_func) == name:
                            self.limiter.limit_manager.add_endpoint_hint(
                                flask.request.endpoint, name
                            )

                    self.limiter._check_request_limit(
                        in_middleware=False, callable_name=name
                    )

                    self.limiter.context.rate_limiting_complete[name] = True
                return cast(
                    R, flask.current_app.ensure_sync(cast(Callable[P, R], obj))(*a, **k)
                )

            return __inner
