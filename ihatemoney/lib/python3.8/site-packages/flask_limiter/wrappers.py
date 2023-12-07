from __future__ import annotations

import dataclasses
import typing
import weakref
from typing import Callable, Iterator, List, Optional, Tuple, Union

from flask import request
from flask.wrappers import Response
from limits import RateLimitItem, parse_many
from limits.strategies import RateLimiter

if typing.TYPE_CHECKING:
    from .extension import Limiter


class RequestLimit:
    """
    Provides details of a rate limit within the context of a request
    """

    #: The instance of the rate limit
    limit: RateLimitItem

    #: The full key for the request against which the rate limit is tested
    key: str

    #: Whether the limit was breached within the context of this request
    breached: bool

    def __init__(
        self,
        extension: Limiter,
        limit: RateLimitItem,
        request_args: List[str],
        breached: bool,
    ) -> None:
        self.extension: weakref.ProxyType[Limiter] = weakref.proxy(extension)
        self.limit = limit
        self.request_args = request_args
        self.key = limit.key_for(*request_args)
        self.breached = breached
        self._window: Optional[Tuple[int, int]] = None

    @property
    def limiter(self) -> RateLimiter:
        return typing.cast(RateLimiter, self.extension.limiter)

    @property
    def window(self) -> Tuple[int, int]:
        if not self._window:
            self._window = self.limiter.get_window_stats(self.limit, *self.request_args)

        return self._window

    @property
    def reset_at(self) -> int:
        """Timestamp at which the rate limit will be reset"""

        return int(self.window[0] + 1)

    @property
    def remaining(self) -> int:
        """Quantity remaining for this rate limit"""

        return self.window[1]


@dataclasses.dataclass(eq=True, unsafe_hash=True)
class Limit:
    """
    simple wrapper to encapsulate limits and their context
    """

    limit: RateLimitItem
    key_func: Callable[[], str]
    _scope: Optional[Union[str, Callable[[str], str]]]
    per_method: bool = False
    methods: Optional[Tuple[str, ...]] = None
    error_message: Optional[str] = None
    exempt_when: Optional[Callable[[], bool]] = None
    override_defaults: Optional[bool] = False
    deduct_when: Optional[Callable[[Response], bool]] = None
    on_breach: Optional[Callable[[RequestLimit], Optional[Response]]] = None
    _cost: Union[Callable[[], int], int] = 1

    def __post_init__(self) -> None:
        if self.methods:
            self.methods = tuple([k.lower() for k in self.methods])

    @property
    def is_exempt(self) -> bool:
        """Check if the limit is exempt."""

        if self.exempt_when:
            return self.exempt_when()
        return False

    @property
    def scope(self) -> Optional[str]:
        return (
            self._scope(request.endpoint or "")
            if callable(self._scope)
            else self._scope
        )

    @property
    def cost(self) -> int:
        if isinstance(self._cost, int):
            return self._cost

        return self._cost()

    @property
    def method_exempt(self) -> bool:
        """Check if the limit is not applicable for this method"""

        return self.methods is not None and request.method.lower() not in self.methods

    def args_for(self, endpoint: str, key: str, method: Optional[str]) -> List[str]:
        scope = self.scope or endpoint
        if self.per_method:
            assert method
            scope += f":{method.upper()}"
        args = [key, scope]
        return args


@dataclasses.dataclass(eq=True, unsafe_hash=True)
class LimitGroup:
    """
    represents a group of related limits either from a string or a callable
    that returns one
    """

    limit_provider: Union[Callable[[], str], str]
    key_function: Callable[[], str]
    scope: Optional[Union[str, Callable[[str], str]]] = None
    methods: Optional[Tuple[str, ...]] = None
    error_message: Optional[str] = None
    exempt_when: Optional[Callable[[], bool]] = None
    override_defaults: Optional[bool] = False
    deduct_when: Optional[Callable[[Response], bool]] = None
    on_breach: Optional[Callable[[RequestLimit], Optional[Response]]] = None
    per_method: bool = False
    cost: Optional[Union[Callable[[], int], int]] = None

    def __iter__(self) -> Iterator[Limit]:
        limit_items = parse_many(
            self.limit_provider()
            if callable(self.limit_provider)
            else self.limit_provider
        )

        for limit in limit_items:
            yield Limit(
                limit,
                self.key_function,
                self.scope,
                self.per_method,
                self.methods,
                self.error_message,
                self.exempt_when,
                self.override_defaults,
                self.deduct_when,
                self.on_breach,
                self.cost or 1,
            )
