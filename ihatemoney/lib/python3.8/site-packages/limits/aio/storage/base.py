from abc import ABC, abstractmethod

from deprecated.sphinx import versionadded

from limits.storage.registry import StorageRegistry
from limits.typing import List, Optional, Tuple, Union
from limits.util import LazyDependency


@versionadded(version="2.1")
class Storage(LazyDependency, metaclass=StorageRegistry):
    """
    Base class to extend when implementing an async storage backend.
    """

    STORAGE_SCHEME: Optional[List[str]]
    """The storage schemes to register against this implementation"""

    def __init__(
        self, uri: Optional[str] = None, **options: Union[float, str, bool]
    ) -> None:
        super().__init__()

    @abstractmethod
    async def incr(
        self, key: str, expiry: int, elastic_expiry: bool = False, amount: int = 1
    ) -> int:
        """
        increments the counter for a given rate limit key

        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        :param elastic_expiry: whether to keep extending the rate limit
         window every hit.
        :param amount: the number to increment by
        """
        raise NotImplementedError

    @abstractmethod
    async def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """
        raise NotImplementedError

    @abstractmethod
    async def get_expiry(self, key: str) -> int:
        """
        :param key: the key to get the expiry for
        """
        raise NotImplementedError

    @abstractmethod
    async def check(self) -> bool:
        """
        check if storage is healthy
        """
        raise NotImplementedError

    @abstractmethod
    async def reset(self) -> Optional[int]:
        """
        reset storage to clear limits
        """
        raise NotImplementedError

    @abstractmethod
    async def clear(self, key: str) -> None:
        """
        resets the rate limit key

        :param key: the key to clear rate limits for
        """
        raise NotImplementedError


class MovingWindowSupport(ABC):
    """
    Abstract base for storages that intend to support
    the moving window strategy
    """

    async def acquire_entry(
        self, key: str, limit: int, expiry: int, amount: int = 1
    ) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param amount: the number of entries to acquire
        """
        raise NotImplementedError

    async def get_moving_window(
        self, key: str, limit: int, expiry: int
    ) -> Tuple[int, int]:
        """
        returns the starting point and the number of entries in the moving
        window

        :param key: rate limit key
        :param expiry: expiry of entry
        :return: (start of window, number of acquired entries)
        """
        raise NotImplementedError
