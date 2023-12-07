import time
import urllib
from typing import TYPE_CHECKING, cast

from deprecated.sphinx import versionadded
from packaging.version import Version

from limits.aio.storage.base import MovingWindowSupport, Storage
from limits.errors import ConfigurationError
from limits.typing import AsyncRedisClient, Dict, Optional, Tuple, Union
from limits.util import get_package_data

if TYPE_CHECKING:
    import coredis
    import coredis.commands


class RedisInteractor:
    RES_DIR = "resources/redis/lua_scripts"

    SCRIPT_MOVING_WINDOW = get_package_data(f"{RES_DIR}/moving_window.lua")
    SCRIPT_ACQUIRE_MOVING_WINDOW = get_package_data(
        f"{RES_DIR}/acquire_moving_window.lua"
    )
    SCRIPT_CLEAR_KEYS = get_package_data(f"{RES_DIR}/clear_keys.lua")
    SCRIPT_INCR_EXPIRE = get_package_data(f"{RES_DIR}/incr_expire.lua")

    lua_moving_window: "coredis.commands.Script[bytes]"
    lua_acquire_window: "coredis.commands.Script[bytes]"
    lua_clear_keys: "coredis.commands.Script[bytes]"
    lua_incr_expire: "coredis.commands.Script[bytes]"

    PREFIX = "LIMITS"

    def prefixed_key(self, key: str) -> str:
        return f"{self.PREFIX}:{key}"

    async def _incr(
        self,
        key: str,
        expiry: int,
        connection: AsyncRedisClient,
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
        value = await connection.incrby(key, amount)

        if elastic_expiry or value == amount:
            await connection.expire(key, expiry)

        return value

    async def _get(self, key: str, connection: AsyncRedisClient) -> int:
        """
        :param connection: Redis connection
        :param key: the key to get the counter value for
        """

        key = self.prefixed_key(key)
        return int(await connection.get(key) or 0)

    async def _clear(self, key: str, connection: AsyncRedisClient) -> None:
        """
        :param key: the key to clear rate limits for
        :param connection: Redis connection
        """
        key = self.prefixed_key(key)
        await connection.delete([key])

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
        key = self.prefixed_key(key)
        timestamp = int(time.time())
        window = await self.lua_moving_window.execute(
            [key], [int(timestamp - expiry), limit]
        )
        if window:
            return tuple(window)  # type: ignore
        return timestamp, 0

    async def _acquire_entry(
        self,
        key: str,
        limit: int,
        expiry: int,
        connection: AsyncRedisClient,
        amount: int = 1,
    ) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param connection: Redis connection
        """
        key = self.prefixed_key(key)
        timestamp = time.time()
        acquired = await self.lua_acquire_window.execute(
            [key], [timestamp, limit, expiry, amount]
        )

        return bool(acquired)

    async def _get_expiry(self, key: str, connection: AsyncRedisClient) -> int:
        """
        :param key: the key to get the expiry for
        :param connection: Redis connection
        """

        key = self.prefixed_key(key)
        return int(max(await connection.ttl(key), 0) + time.time())

    async def _check(self, connection: AsyncRedisClient) -> bool:
        """
        check if storage is healthy

        :param connection: Redis connection
        """
        try:
            await connection.ping()

            return True
        except:  # noqa
            return False


@versionadded(version="2.1")
class RedisStorage(RedisInteractor, Storage, MovingWindowSupport):
    """
    Rate limit storage with redis as backend.

    Depends on :pypi:`coredis`
    """

    STORAGE_SCHEME = ["async+redis", "async+rediss", "async+redis+unix"]
    """
    The storage schemes for redis to be used in an async context
    """
    DEPENDENCIES = {"coredis": Version("3.4.0")}

    def __init__(
        self,
        uri: str,
        connection_pool: Optional["coredis.ConnectionPool"] = None,
        **options: Union[float, str, bool],
    ) -> None:
        """
        :param uri: uri of the form:

         - ``async+redis://[:password]@host:port``
         - ``async+redis://[:password]@host:port/db``
         - ``async+rediss://[:password]@host:port``
         - ``async+unix:///path/to/sock`` etc...

         This uri is passed directly to :meth:`coredis.Redis.from_url` with
         the initial ``async`` removed, except for the case of ``async+redis+unix``
         where it is replaced with ``unix``.
        :param connection_pool: if provided, the redis client is initialized with
         the connection pool and any other params passed as :paramref:`options`
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`coredis.Redis`
        :raise ConfigurationError: when the redis library is not available
        """
        uri = uri.replace("async+redis", "redis", 1)
        uri = uri.replace("redis+unix", "unix")

        super().__init__(uri, **options)

        self.dependency = self.dependencies["coredis"].module

        if connection_pool:
            self.storage = self.dependency.Redis(
                connection_pool=connection_pool, **options
            )
        else:
            self.storage = self.dependency.Redis.from_url(uri, **options)

        self.initialize_storage(uri)

    def initialize_storage(self, _uri: str) -> None:
        # all these methods are coroutines, so must be called with await
        self.lua_moving_window = self.storage.register_script(self.SCRIPT_MOVING_WINDOW)
        self.lua_acquire_window = self.storage.register_script(
            self.SCRIPT_ACQUIRE_MOVING_WINDOW
        )
        self.lua_clear_keys = self.storage.register_script(self.SCRIPT_CLEAR_KEYS)
        self.lua_incr_expire = self.storage.register_script(
            RedisStorage.SCRIPT_INCR_EXPIRE
        )

    async def incr(
        self, key: str, expiry: int, elastic_expiry: bool = False, amount: int = 1
    ) -> int:
        """
        increments the counter for a given rate limit key

        :param key: the key to increment
        :param expiry: amount in seconds for the key to expire in
        :param amount: the number to increment by
        """

        if elastic_expiry:
            return await super()._incr(
                key, expiry, self.storage, elastic_expiry, amount
            )
        else:
            key = self.prefixed_key(key)
            return cast(
                int, await self.lua_incr_expire.execute([key], [expiry, amount])
            )

    async def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """

        return await super()._get(key, self.storage)

    async def clear(self, key: str) -> None:
        """
        :param key: the key to clear rate limits for
        """

        return await super()._clear(key, self.storage)

    async def acquire_entry(
        self, key: str, limit: int, expiry: int, amount: int = 1
    ) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param amount: the number of entries to acquire
        """

        return await super()._acquire_entry(key, limit, expiry, self.storage, amount)

    async def get_expiry(self, key: str) -> int:
        """
        :param key: the key to get the expiry for
        """

        return await super()._get_expiry(key, self.storage)

    async def check(self) -> bool:
        """
        Check if storage is healthy by calling :meth:`coredis.Redis.ping`
        """

        return await super()._check(self.storage)

    async def reset(self) -> Optional[int]:
        """
        This function calls a Lua Script to delete keys prefixed with `self.PREFIX`
        in block of 5000.

        .. warning:: This operation was designed to be fast, but was not tested
           on a large production based system. Be careful with its usage as it
           could be slow on very large data sets.
        """

        prefix = self.prefixed_key("*")
        return cast(int, await self.lua_clear_keys.execute([prefix]))


@versionadded(version="2.1")
class RedisClusterStorage(RedisStorage):
    """
    Rate limit storage with redis cluster as backend

    Depends on :pypi:`coredis`
    """

    STORAGE_SCHEME = ["async+redis+cluster"]
    """
    The storage schemes for redis cluster to be used in an async context
    """

    DEFAULT_OPTIONS: Dict[str, Union[float, str, bool]] = {
        "max_connections": 1000,
    }
    "Default options passed to :class:`coredis.RedisCluster`"

    def __init__(self, uri: str, **options: Union[float, str, bool]) -> None:
        """
        :param uri: url of the form
         ``async+redis+cluster://[:password]@host:port,host:port``
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`coredis.RedisCluster`
        :raise ConfigurationError: when the coredis library is not
         available or if the redis host cannot be pinged.
        """
        parsed = urllib.parse.urlparse(uri)
        parsed_auth: Dict[str, Union[float, str, bool]] = {}

        if parsed.username:
            parsed_auth["username"] = parsed.username
        if parsed.password:
            parsed_auth["password"] = parsed.password

        sep = parsed.netloc.find("@") + 1
        cluster_hosts = []

        for loc in parsed.netloc[sep:].split(","):
            host, port = loc.split(":")
            cluster_hosts.append({"host": host, "port": int(port)})

        super(RedisStorage, self).__init__(uri, **options)

        self.dependency = self.dependencies["coredis"].module

        self.storage: "coredis.RedisCluster[str]" = self.dependency.RedisCluster(
            startup_nodes=cluster_hosts,
            **{**self.DEFAULT_OPTIONS, **parsed_auth, **options},
        )
        self.initialize_storage(uri)

    async def reset(self) -> Optional[int]:
        """
        Redis Clusters are sharded and deleting across shards
        can't be done atomically. Because of this, this reset loops over all
        keys that are prefixed with `self.PREFIX` and calls delete on them,
        one at a time.

        .. warning:: This operation was not tested with extremely large data sets.
           On a large production based system, care should be taken with its
           usage as it could be slow on very large data sets
        """

        prefix = self.prefixed_key("*")
        keys = await self.storage.keys(prefix)
        count = 0
        for key in keys:
            count += await self.storage.delete([key])
        return count


@versionadded(version="2.1")
class RedisSentinelStorage(RedisStorage):
    """
    Rate limit storage with redis sentinel as backend

    Depends on :pypi:`coredis`
    """

    STORAGE_SCHEME = ["async+redis+sentinel"]
    """The storage scheme for redis accessed via a redis sentinel installation"""

    DEPENDENCIES = {"coredis.sentinel": Version("3.4.0")}

    def __init__(
        self,
        uri: str,
        service_name: Optional[str] = None,
        use_replicas: bool = True,
        sentinel_kwargs: Optional[Dict[str, Union[float, str, bool]]] = None,
        **options: Union[float, str, bool],
    ):
        """
        :param uri: url of the form
         ``async+redis+sentinel://host:port,host:port/service_name``
        :param service_name, optional: sentinel service name
         (if not provided in `uri`)
        :param use_replicas: Whether to use replicas for read only operations
        :param sentinel_kwargs, optional: kwargs to pass as
         ``sentinel_kwargs`` to :class:`coredis.sentinel.Sentinel`
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`coredis.sentinel.Sentinel`
        :raise ConfigurationError: when the coredis library is not available
         or if the redis primary host cannot be pinged.
        """

        parsed = urllib.parse.urlparse(uri)
        sentinel_configuration = []
        connection_options = options.copy()
        sentinel_options = sentinel_kwargs.copy() if sentinel_kwargs else {}
        parsed_auth: Dict[str, Union[float, str, bool]] = {}

        if parsed.username:
            parsed_auth["username"] = parsed.username

        if parsed.password:
            parsed_auth["password"] = parsed.password

        sep = parsed.netloc.find("@") + 1

        for loc in parsed.netloc[sep:].split(","):
            host, port = loc.split(":")
            sentinel_configuration.append((host, int(port)))
        self.service_name = (
            parsed.path.replace("/", "") if parsed.path else service_name
        )

        if self.service_name is None:
            raise ConfigurationError("'service_name' not provided")

        super(RedisStorage, self).__init__()

        self.dependency = self.dependencies["coredis.sentinel"].module

        self.sentinel = self.dependency.Sentinel(
            sentinel_configuration,
            sentinel_kwargs={**parsed_auth, **sentinel_options},
            **{**parsed_auth, **connection_options},
        )
        self.storage = self.sentinel.primary_for(self.service_name)
        self.storage_replica = self.sentinel.replica_for(self.service_name)
        self.use_replicas = use_replicas
        self.initialize_storage(uri)

    async def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """

        return await super()._get(
            key, self.storage_replica if self.use_replicas else self.storage
        )

    async def get_expiry(self, key: str) -> int:
        """
        :param key: the key to get the expiry for
        """

        return await super()._get_expiry(
            key, self.storage_replica if self.use_replicas else self.storage
        )

    async def check(self) -> bool:
        """
        Check if storage is healthy by calling :meth:`coredis.Redis.ping`
        on the replica.
        """

        return await super()._check(
            self.storage_replica if self.use_replicas else self.storage
        )
