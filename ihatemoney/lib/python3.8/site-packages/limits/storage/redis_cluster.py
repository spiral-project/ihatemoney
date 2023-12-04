import urllib
import warnings
from typing import cast

from deprecated.sphinx import versionchanged
from packaging.version import Version

from limits.errors import ConfigurationError
from limits.storage.redis import RedisStorage
from limits.typing import Dict, List, Optional, Tuple, Union


@versionchanged(
    version="2.5.0",
    reason="""
Cluster support was provided by the :pypi:`redis-py-cluster` library
which has been absorbed into the official :pypi:`redis` client. By
default the :class:`redis.cluster.RedisCluster` client will be used
however if the version of the package is lower than ``4.2.0`` the implementation
will fallback to trying to use :class:`rediscluster.RedisCluster`.
""",
)
class RedisClusterStorage(RedisStorage):
    """
    Rate limit storage with redis cluster as backend

    Depends on :pypi:`redis`.
    """

    STORAGE_SCHEME = ["redis+cluster"]
    """The storage scheme for redis cluster"""

    DEFAULT_OPTIONS: Dict[str, Union[float, str, bool]] = {
        "max_connections": 1000,
    }
    "Default options passed to the :class:`~redis.cluster.RedisCluster`"

    DEPENDENCIES = {
        "redis": Version("4.2.0"),
        "rediscluster": Version("2.0.0"),  # Deprecated since 2.6.0
    }

    def __init__(self, uri: str, **options: Union[float, str, bool]) -> None:
        """
        :param uri: url of the form
         ``redis+cluster://[:password]@host:port,host:port``
        :param options: all remaining keyword arguments are passed
         directly to the constructor of :class:`redis.cluster.RedisCluster`
        :raise ConfigurationError: when the :pypi:`redis` library is not
         available or if the redis cluster cannot be reached.
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
            cluster_hosts.append((host, int(port)))

        self.storage = None
        self.using_redis_py = False
        self.__pick_storage(
            cluster_hosts, **{**self.DEFAULT_OPTIONS, **parsed_auth, **options}
        )
        assert self.storage
        self.initialize_storage(uri)
        super(RedisStorage, self).__init__(uri, **options)

    def __pick_storage(
        self, cluster_hosts: List[Tuple[str, int]], **options: Union[float, str, bool]
    ) -> None:
        try:
            redis_py = self.dependencies["redis"].module
            startup_nodes = [redis_py.cluster.ClusterNode(*c) for c in cluster_hosts]
            self.storage = redis_py.cluster.RedisCluster(
                startup_nodes=startup_nodes, **options
            )
            self.using_redis_py = True
            return
        except ConfigurationError:  # pragma: no cover
            self.__use_legacy_cluster_implementation(cluster_hosts, **options)
            if not self.storage:
                raise ConfigurationError(
                    (
                        "Unable to find an implementation for redis cluster"
                        " Cluster support requires either redis-py>=4.2 or"
                        " redis-py-cluster"
                    )
                )

    def __use_legacy_cluster_implementation(
        self, cluster_hosts: List[Tuple[str, int]], **options: Union[float, str, bool]
    ) -> None:  # pragma: no cover
        redis_cluster = self.dependencies["rediscluster"].module
        warnings.warn(
            (
                "Using redis-py-cluster is deprecated as the library has been"
                " absorbed by redis-py (>=4.2). The support will be eventually "
                " removed from the limits library and is no longer tested "
                " against since version: 2.6. To get rid of this warning, "
                " uninstall redis-py-cluster and ensure redis-py>=4.2.0 is installed"
            )
        )
        self.storage = redis_cluster.RedisCluster(
            startup_nodes=[{"host": c[0], "port": c[1]} for c in cluster_hosts],
            **options,
        )

    def reset(self) -> Optional[int]:
        """
        Redis Clusters are sharded and deleting across shards
        can't be done atomically. Because of this, this reset loops over all
        keys that are prefixed with `self.PREFIX` and calls delete on them,
        one at a time.

        .. warning::
         This operation was not tested with extremely large data sets.
         On a large production based system, care should be taken with its
         usage as it could be slow on very large data sets"""

        prefix = self.prefixed_key("*")
        if self.using_redis_py:
            count = 0
            for primary in self.storage.get_primaries():
                node = self.storage.get_redis_connection(primary)
                keys = node.keys(prefix)
                count += sum([node.delete(k.decode("utf-8")) for k in keys])
            return count
        else:  # pragma: no cover
            keys = self.storage.keys(prefix)
            return cast(
                int, sum([self.storage.delete(k.decode("utf-8")) for k in keys])
            )
