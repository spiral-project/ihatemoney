from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from typing_extensions import ClassVar, Counter, ParamSpec, Protocol

Serializable = Union[int, str, float]

R = TypeVar("R")
R_co = TypeVar("R_co", covariant=True)
P = ParamSpec("P")


if TYPE_CHECKING:
    import coredis
    import coredis.commands.script
    import redis


class ItemP(Protocol):
    value: bytes
    flags: Optional[int]
    cas: Optional[int]


class EmcacheClientP(Protocol):
    async def add(
        self,
        key: bytes,
        value: bytes,
        *,
        flags: int = 0,
        exptime: int = 0,
        noreply: bool = False,
    ) -> None:
        ...

    async def get(self, key: bytes, return_flags: bool = False) -> Optional[ItemP]:
        ...

    async def gets(self, key: bytes, return_flags: bool = False) -> Optional[ItemP]:
        ...

    async def increment(
        self, key: bytes, value: int, *, noreply: bool = False
    ) -> Optional[int]:
        ...

    async def delete(self, key: bytes, *, noreply: bool = False) -> None:
        ...

    async def set(
        self,
        key: bytes,
        value: bytes,
        *,
        flags: int = 0,
        exptime: int = 0,
        noreply: bool = False,
    ) -> None:
        ...

    async def touch(self, key: bytes, exptime: int, *, noreply: bool = False) -> None:
        ...


class MemcachedClientP(Protocol):
    def add(
        self,
        key: str,
        value: Serializable,
        expire: Optional[int] = 0,
        noreply: Optional[bool] = None,
        flags: Optional[int] = None,
    ) -> bool:
        ...

    def get(self, key: str, default: Optional[str] = None) -> bytes:
        ...

    def incr(self, key: str, value: int, noreply: Optional[bool] = False) -> int:
        ...

    def delete(self, key: str, noreply: Optional[bool] = None) -> Optional[bool]:
        ...

    def set(
        self,
        key: str,
        value: Serializable,
        expire: int = 0,
        noreply: Optional[bool] = None,
        flags: Optional[int] = None,
    ) -> bool:
        ...

    def touch(
        self, key: str, expire: Optional[int] = 0, noreply: Optional[bool] = None
    ) -> bool:
        ...


AsyncRedisClient = Union["coredis.Redis[bytes]", "coredis.RedisCluster[bytes]"]
RedisClient = Union["redis.Redis[bytes]", "redis.cluster.RedisCluster[bytes]"]


class ScriptP(Protocol[R_co]):
    def __call__(self, keys: List[Serializable], args: List[Serializable]) -> R_co:
        ...


__all__ = [
    "AsyncRedisClient",
    "Callable",
    "ClassVar",
    "Counter",
    "Dict",
    "EmcacheClientP",
    "ItemP",
    "List",
    "MemcachedClientP",
    "NamedTuple",
    "Optional",
    "P",
    "ParamSpec",
    "Protocol",
    "ScriptP",
    "Serializable",
    "TypeVar",
    "R",
    "R_co",
    "RedisClient",
    "Tuple",
    "Type",
    "TypeVar",
    "Union",
]
