"""
Implementations of storage backends to be used with
:class:`limits.aio.strategies.RateLimiter` strategies
"""

from .base import MovingWindowSupport, Storage
from .etcd import EtcdStorage
from .memcached import MemcachedStorage
from .memory import MemoryStorage
from .mongodb import MongoDBStorage
from .redis import RedisClusterStorage, RedisSentinelStorage, RedisStorage

__all__ = [
    "Storage",
    "MovingWindowSupport",
    "EtcdStorage",
    "MemcachedStorage",
    "MemoryStorage",
    "MongoDBStorage",
    "RedisStorage",
    "RedisClusterStorage",
    "RedisSentinelStorage",
]
