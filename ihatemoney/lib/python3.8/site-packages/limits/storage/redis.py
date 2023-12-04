from __future__ import annotations

import time
from typing import TYPE_CHECKING

from packaging.version import Version

from limits.typing import Optional, RedisClient, ScriptP, Tuple, Union

from ..util import get_package_data
from .base import MovingWindowSupport, Storage

if TYPE_CHECKING:
    import redis


class RedisInteractor:
    RES_DIR = "resources/redis/lua_scripts"

    SCRIPT_MOVING_WINDOW = get_package_data(f"{RES_DIR}/moving_window.lua")
    SCRIPT_ACQUIRE_MOVING_WINDOW = get_package_data(
        f"{RES_DIR}/acquire_moving_window.lua"
    )
    SCRIPT_CLEAR_KEYS = get_package_data(f"{RES_DIR}/clear_keys.lua")
    SCRIPT_INCR_EXPIRE = get_package_data(f"{RES_DIR}/incr_expire.lua")

    lua_moving_window: ScriptP[Tuple[int, int]]
    lua_acquire_window: ScriptP[bool]

    PREFIX = "LIMITS"

    def prefixed_key(self, key: str) -> str:
        return f"{self.PREFIX}:{key}"

    def get_moving_window(self, key: str, limit: int, expiry: int) -> Tuple[int, int]:
        """
        returns the starting point and the number of entries in the moving
        window

        :param key: rate limit key
        :param expiry: expiry of entry
        :return: (start of window, number of acquired entries)
        """
        key = self.prefixed_key(key)
        timestamp = time.time()
        window = self.lua_moving_window([key], [int(timestamp - expiry), limit])

        return window or (int(timestamp), 0)

    def _incr(
        self,
        key: str,
        expiry: int,
        connection: RedisClient,
        elastic_expiry: bool = False,
        amount: int = 1,
    ) -> int:
        """
        increments the counter for a given rate limit key

        :param connection: Redis connection
        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        :param amount: the number to increment by
        """
        key = self.prefixed_key(key)
        value = connection.incrby(key, amount)

        if elastic_expiry or value == amount:
            connection.expire(key, expiry)

        return value

    def _get(self, key: str, connection: RedisClient) -> int:
        """
        :param connection: Redis connection
        :param key: the key to get the counter value for
        """

        key = self.prefixed_key(key)
        return int(connection.get(key) or 0)

    def _clear(self, key: str, connection: RedisClient) -> None:
        """
        :param key: the key to clear rate limits for
        :param connection: Redis connection
        """
        key = self.prefixed_key(key)
        connection.delete(key)

    def _acquire_entry(
        self,
        key: str,
        limit: int,
        expiry: int,
        connection: RedisClient,
        amount: int = 1,
    ) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param connection: Redis connection
        :param amount: the number of entries to acquire
        """
        key = self.prefixed_key(key)
        timestamp = time.time()
        acquired = self.lua_acquire_window([key], [timestamp, limit, expiry, amount])

        return bool(acquired)

    def _get_expiry(self, key: str, connection: RedisClient) -> int:
        """
        :param key: the key to get the expiry for
        :param connection: Redis connection
        """

        key = self.prefixed_key(key)
        return int(max(connection.ttl(key), 0) + time.time())

    def _check(self, connection: RedisClient) -> bool:
        """
        :param connection: Redis connection
        check if storage is healthy
        """
        try:
            return connection.ping()
        except:  # noqa
            return False


class RedisStorage(RedisInteractor, Storage, MovingWindowSupport):
    """
    Rate limit storage with redis as backend.

    Depends on :pypi:`redis`.
    """

    STORAGE_SCHEME = ["redis", "rediss", "redis+unix"]
    """The storage scheme for redis"""

    DEPENDENCIES = {"redis": Version("3.0")}

    def __init__(
        self,
        uri: str,
        connection_pool: Optional[redis.connection.ConnectionPool] = None,
        **options: Union[float, str, bool],
    ) -> None:
        """
        :param uri: uri of the form ``redis://[:password]@host:port``,
         ``redis://[:password]@host:port/db``,
         ``rediss://[:password]@host:port``, ``redis+unix:///path/to/sock`` etc.
         This uri is passed directly to :func:`redis.from_url` except for the
         case of ``redis+unix://`` where it is replaced with ``unix://``.
        :param connection_pool: if provided, the redis client is initialized with
         the connection pool and any other params passed as :paramref:`options`
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`redis.Redis`
        :raise ConfigurationError: when the :pypi:`redis` library is not available
        """
        super().__init__(uri, **options)
        redis = self.dependencies["redis"].module

        uri = uri.replace("redis+unix", "unix")

        if not connection_pool:
            self.storage = redis.from_url(uri, **options)
        else:
            self.storage = redis.Redis(connection_pool=connection_pool, **options)
        self.initialize_storage(uri)

    def initialize_storage(self, _uri: str) -> None:
        self.lua_moving_window = self.storage.register_script(self.SCRIPT_MOVING_WINDOW)
        self.lua_acquire_window = self.storage.register_script(
            self.SCRIPT_ACQUIRE_MOVING_WINDOW
        )
        self.lua_clear_keys = self.storage.register_script(self.SCRIPT_CLEAR_KEYS)
        self.lua_incr_expire = self.storage.register_script(
            RedisStorage.SCRIPT_INCR_EXPIRE
        )

    def incr(
        self, key: str, expiry: int, elastic_expiry: bool = False, amount: int = 1
    ) -> int:
        """
        increments the counter for a given rate limit key

        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        :param amount: the number to increment by
        """

        if elastic_expiry:
            return super()._incr(key, expiry, self.storage, elastic_expiry, amount)
        else:
            key = self.prefixed_key(key)
            return int(self.lua_incr_expire([key], [expiry, amount]))

    def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """

        return super()._get(key, self.storage)

    def clear(self, key: str) -> None:
        """
        :param key: the key to clear rate limits for
        """

        return super()._clear(key, self.storage)

    def acquire_entry(self, key: str, limit: int, expiry: int, amount: int = 1) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param amount: the number to increment by
        """

        return super()._acquire_entry(key, limit, expiry, self.storage, amount)

    def get_expiry(self, key: str) -> int:
        """
        :param key: the key to get the expiry for
        """

        return super()._get_expiry(key, self.storage)

    def check(self) -> bool:
        """
        check if storage is healthy
        """

        return super()._check(self.storage)

    def reset(self) -> Optional[int]:
        """
        This function calls a Lua Script to delete keys prefixed with `self.PREFIX`
        in block of 5000.

        .. warning::
           This operation was designed to be fast, but was not tested
           on a large production based system. Be careful with its usage as it
           could be slow on very large data sets.

        """

        prefix = self.prefixed_key("*")
        return int(self.lua_clear_keys([prefix]))
