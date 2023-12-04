import time
import urllib.parse

from deprecated.sphinx import versionadded

from limits.aio.storage.base import Storage
from limits.typing import EmcacheClientP, Optional, Union


@versionadded(version="2.1")
class MemcachedStorage(Storage):
    """
    Rate limit storage with memcached as backend.

    Depends on :pypi:`emcache`
    """

    STORAGE_SCHEME = ["async+memcached"]
    """The storage scheme for memcached to be used in an async context"""

    DEPENDENCIES = ["emcache"]

    def __init__(self, uri: str, **options: Union[float, str, bool]) -> None:
        """
        :param uri: memcached location of the form
         ``async+memcached://host:port,host:port``
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`emcache.Client`
        :raise ConfigurationError: when :pypi:`emcache` is not available
        """
        parsed = urllib.parse.urlparse(uri)
        self.hosts = []

        for host, port in (
            loc.split(":") for loc in parsed.netloc.strip().split(",") if loc.strip()
        ):
            self.hosts.append((host, int(port)))

        self._options = options
        self._storage = None
        super().__init__(uri, **options)
        self.dependency = self.dependencies["emcache"].module

    async def get_storage(self) -> EmcacheClientP:
        if not self._storage:
            self._storage = await self.dependency.create_client(
                [self.dependency.MemcachedHostAddress(h, p) for h, p in self.hosts],
                **self._options,
            )
        assert self._storage
        return self._storage

    async def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """

        item = await (await self.get_storage()).get(key.encode("utf-8"))

        return item and int(item.value) or 0

    async def clear(self, key: str) -> None:
        """
        :param key: the key to clear rate limits for
        """
        await (await self.get_storage()).delete(key.encode("utf-8"))

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
        storage = await self.get_storage()
        limit_key = key.encode("utf-8")
        expire_key = f"{key}/expires".encode()
        added = True
        try:
            await storage.add(limit_key, f"{amount}".encode(), exptime=expiry)
        except self.dependency.NotStoredStorageCommandError:
            added = False
            storage = await self.get_storage()

        if not added:
            value = await storage.increment(limit_key, amount) or amount

            if elastic_expiry:
                await storage.touch(limit_key, exptime=expiry)
                await storage.set(
                    expire_key,
                    str(expiry + time.time()).encode("utf-8"),
                    exptime=expiry,
                    noreply=False,
                )

            return value
        else:
            await storage.set(
                expire_key,
                str(expiry + time.time()).encode("utf-8"),
                exptime=expiry,
                noreply=False,
            )

        return amount

    async def get_expiry(self, key: str) -> int:
        """
        :param key: the key to get the expiry for
        """
        storage = await self.get_storage()
        item = await storage.get(f"{key}/expires".encode())

        return int(item and float(item.value) or time.time())

    async def check(self) -> bool:
        """
        Check if storage is healthy by calling the ``get`` command
        on the key ``limiter-check``
        """
        try:
            storage = await self.get_storage()
            await storage.get(b"limiter-check")

            return True
        except:  # noqa
            return False

    async def reset(self) -> Optional[int]:
        raise NotImplementedError
