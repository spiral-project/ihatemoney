"""
Implementations of storage backends to be used with
:class:`limits.strategies.RateLimiter` strategies
"""

import urllib
from typing import Union, cast

import limits

from ..errors import ConfigurationError
from .base import MovingWindowSupport, Storage
from .etcd import EtcdStorage
from .memcached import MemcachedStorage
from .memory import MemoryStorage
from .mongodb import MongoDBStorage
from .redis import RedisStorage
from .redis_cluster import RedisClusterStorage
from .redis_sentinel import RedisSentinelStorage
from .registry import SCHEMES

StorageTypes = Union[Storage, "limits.aio.storage.Storage"]


def storage_from_string(
    storage_string: str, **options: Union[float, str, bool]
) -> StorageTypes:
    """
    Factory function to get an instance of the storage class based
    on the uri of the storage. In most cases using it should be sufficient
    instead of directly instantiating the storage classes. for example::

        from limits.storage import storage_from_string

        memory = from_string("memory://")
        memcached = from_string("memcached://localhost:11211")
        redis = from_string("redis://localhost:6379")

    The same function can be used to construct the :ref:`storage:async storage`
    variants, for example::

        from limits.storage import storage_from_string

        memory = storage_from_string("async+memory://")
        memcached = storage_from_string("async+memcached://localhost:11211")
        redis = storage_from_string("async+redis://localhost:6379")

    :param storage_string: a string of the form ``scheme://host:port``.
     More details about supported storage schemes can be found at
     :ref:`storage:storage scheme`
    :param options: all remaining keyword arguments are passed to the
     constructor matched by :paramref:`storage_string`.
    :raises ConfigurationError: when the :attr:`storage_string` cannot be
     mapped to a registered :class:`limits.storage.Storage`
     or :class:`limits.aio.storage.Storage` instance.


    """
    scheme = urllib.parse.urlparse(storage_string).scheme

    if scheme not in SCHEMES:
        raise ConfigurationError("unknown storage scheme : %s" % storage_string)
    return cast(StorageTypes, SCHEMES[scheme](storage_string, **options))


__all__ = [
    "storage_from_string",
    "Storage",
    "MovingWindowSupport",
    "EtcdStorage",
    "MemoryStorage",
    "MongoDBStorage",
    "RedisStorage",
    "RedisClusterStorage",
    "RedisSentinelStorage",
    "MemcachedStorage",
]
