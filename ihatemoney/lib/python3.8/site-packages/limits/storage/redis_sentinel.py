import urllib.parse
from typing import TYPE_CHECKING

from packaging.version import Version

from limits.errors import ConfigurationError
from limits.storage.redis import RedisStorage
from limits.typing import Dict, Optional, Union

if TYPE_CHECKING:
    import redis.sentinel


class RedisSentinelStorage(RedisStorage):
    """
    Rate limit storage with redis sentinel as backend

    Depends on :pypi:`redis` package
    """

    STORAGE_SCHEME = ["redis+sentinel"]
    """The storage scheme for redis accessed via a redis sentinel installation"""

    DEPENDENCIES = {"redis.sentinel": Version("3.0")}

    def __init__(
        self,
        uri: str,
        service_name: Optional[str] = None,
        use_replicas: bool = True,
        sentinel_kwargs: Optional[Dict[str, Union[float, str, bool]]] = None,
        **options: Union[float, str, bool]
    ) -> None:
        """
        :param uri: url of the form
         ``redis+sentinel://host:port,host:port/service_name``
        :param service_name: sentinel service name
         (if not provided in :attr:`uri`)
        :param use_replicas: Whether to use replicas for read only operations
        :param sentinel_kwargs: kwargs to pass as
         :attr:`sentinel_kwargs` to :class:`redis.sentinel.Sentinel`
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`redis.sentinel.Sentinel`
        :raise ConfigurationError: when the redis library is not available
         or if the redis master host cannot be pinged.
        """

        super(RedisStorage, self).__init__(uri, **options)

        parsed = urllib.parse.urlparse(uri)
        sentinel_configuration = []
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

        sentinel_dep = self.dependencies["redis.sentinel"].module
        self.sentinel: "redis.sentinel.Sentinel" = sentinel_dep.Sentinel(
            sentinel_configuration,
            sentinel_kwargs={**parsed_auth, **sentinel_options},
            **{**parsed_auth, **options}
        )
        self.storage = self.sentinel.master_for(self.service_name)
        self.storage_slave = self.sentinel.slave_for(self.service_name)
        self.use_replicas = use_replicas
        self.initialize_storage(uri)

    def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """

        return super()._get(
            key, self.storage_slave if self.use_replicas else self.storage
        )

    def get_expiry(self, key: str) -> int:
        """
        :param key: the key to get the expiry for
        """

        return super()._get_expiry(
            key, self.storage_slave if self.use_replicas else self.storage
        )

    def check(self) -> bool:
        """
        Check if storage is healthy by calling :class:`aredis.StrictRedis.ping`
        on the slave.
        """

        return super()._check(self.storage_slave if self.use_replicas else self.storage)
