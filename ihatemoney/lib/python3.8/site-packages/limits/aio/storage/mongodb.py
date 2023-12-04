from __future__ import annotations

import asyncio
import calendar
import datetime
import time
from typing import Any, cast

from deprecated.sphinx import versionadded

from limits.aio.storage.base import MovingWindowSupport, Storage
from limits.typing import Dict, Optional, ParamSpec, Tuple, TypeVar, Union

P = ParamSpec("P")
R = TypeVar("R")


@versionadded(version="2.1")
class MongoDBStorage(Storage, MovingWindowSupport):
    """
    Rate limit storage with MongoDB as backend.

    Depends on :pypi:`motor`
    """

    STORAGE_SCHEME = ["async+mongodb", "async+mongodb+srv"]
    """
    The storage scheme for MongoDB for use in an async context
    """

    DEFAULT_OPTIONS: Dict[str, Union[float, str, bool]] = {
        "serverSelectionTimeoutMS": 1000,
        "connectTimeoutMS": 1000,
    }
    "Default options passed to :class:`~motor.motor_asyncio.AsyncIOMotorClient`"

    DEPENDENCIES = ["motor.motor_asyncio", "pymongo"]

    def __init__(
        self,
        uri: str,
        database_name: str = "limits",
        **options: Union[float, str, bool],
    ) -> None:
        """
        :param uri: uri of the form ``async+mongodb://[user:password]@host:port?...``,
         This uri is passed directly to :class:`~motor.motor_asyncio.AsyncIOMotorClient`
        :param database_name: The database to use for storing the rate limit
         collections.
        :param options: all remaining keyword arguments are merged with
         :data:`DEFAULT_OPTIONS` and passed to the constructor of
         :class:`~motor.motor_asyncio.AsyncIOMotorClient`
        :raise ConfigurationError: when the :pypi:`motor` or :pypi:`pymongo` are
         not available
        """

        mongo_opts = options.copy()
        [mongo_opts.setdefault(k, v) for k, v in self.DEFAULT_OPTIONS.items()]
        uri = uri.replace("async+mongodb", "mongodb", 1)

        super().__init__(uri, **options)

        self.dependency = self.dependencies["motor.motor_asyncio"]
        self.proxy_dependency = self.dependencies["pymongo"]

        self.storage = self.dependency.module.AsyncIOMotorClient(uri, **mongo_opts)
        # TODO: Fix this hack. It was noticed when running a benchmark
        # with FastAPI - however - doesn't appear in unit tests or in an isolated
        # use. Reference: https://jira.mongodb.org/browse/MOTOR-822
        self.storage.get_io_loop = asyncio.get_running_loop

        self.__database_name = database_name
        self.__indices_created = False

    @property
    def database(self):  # type: ignore
        return self.storage.get_database(self.__database_name)

    async def create_indices(self) -> None:
        if not self.__indices_created:
            await asyncio.gather(
                self.database.counters.create_index("expireAt", expireAfterSeconds=0),
                self.database.windows.create_index("expireAt", expireAfterSeconds=0),
            )
        self.__indices_created = True

    async def reset(self) -> Optional[int]:
        """
        Delete all rate limit keys in the rate limit collections (counters, windows)
        """
        num_keys = sum(
            await asyncio.gather(
                self.database.counters.count_documents({}),
                self.database.windows.count_documents({}),
            )
        )
        await asyncio.gather(
            self.database.counters.drop(), self.database.windows.drop()
        )

        return cast(int, num_keys)

    async def clear(self, key: str) -> None:
        """
        :param key: the key to clear rate limits for
        """
        await asyncio.gather(
            self.database.counters.find_one_and_delete({"_id": key}),
            self.database.windows.find_one_and_delete({"_id": key}),
        )

    async def get_expiry(self, key: str) -> int:
        """
        :param key: the key to get the expiry for
        """
        counter = await self.database.counters.find_one({"_id": key})
        expiry = counter["expireAt"] if counter else datetime.datetime.utcnow()

        return calendar.timegm(expiry.timetuple())

    async def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """
        counter = await self.database.counters.find_one(
            {"_id": key, "expireAt": {"$gte": datetime.datetime.utcnow()}},
            projection=["count"],
        )

        return counter and counter["count"] or 0

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
        await self.create_indices()

        expiration = datetime.datetime.utcnow() + datetime.timedelta(seconds=expiry)

        response = await self.database.counters.find_one_and_update(
            {"_id": key},
            [
                {
                    "$set": {
                        "count": {
                            "$cond": {
                                "if": {"$lt": ["$expireAt", "$$NOW"]},
                                "then": amount,
                                "else": {"$add": ["$count", amount]},
                            }
                        },
                        "expireAt": {
                            "$cond": {
                                "if": {"$lt": ["$expireAt", "$$NOW"]},
                                "then": expiration,
                                "else": (expiration if elastic_expiry else "$expireAt"),
                            }
                        },
                    }
                },
            ],
            upsert=True,
            projection=["count"],
            return_document=self.proxy_dependency.module.ReturnDocument.AFTER,
        )

        return int(response["count"])

    async def check(self) -> bool:
        """
        Check if storage is healthy by calling
        :meth:`motor.motor_asyncio.AsyncIOMotorClient.server_info`
        """
        try:
            await self.storage.server_info()

            return True
        except:  # noqa: E722
            return False

    async def get_moving_window(
        self, key: str, limit: int, expiry: int
    ) -> Tuple[int, int]:
        """
        returns the starting point and the number of entries in the moving
        window

        :param str key: rate limit key
        :param int expiry: expiry of entry
        :return: (start of window, number of acquired entries)
        """
        timestamp = time.time()
        result = await self.database.windows.aggregate(
            [
                {"$match": {"_id": key}},
                {
                    "$project": {
                        "entries": {
                            "$filter": {
                                "input": "$entries",
                                "as": "entry",
                                "cond": {"$gte": ["$$entry", timestamp - expiry]},
                            }
                        }
                    }
                },
                {"$unwind": "$entries"},
                {
                    "$group": {
                        "_id": "$_id",
                        "max": {"$max": "$entries"},
                        "count": {"$sum": 1},
                    }
                },
            ]
        ).to_list(length=1)

        if result:
            return (int(result[0]["max"]), result[0]["count"])

        return (int(timestamp), 0)

    async def acquire_entry(
        self, key: str, limit: int, expiry: int, amount: int = 1
    ) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param amount: the number of entries to acquire
        """
        await self.create_indices()

        if amount > limit:
            return False

        timestamp = time.time()
        try:
            updates: Dict[str, Any] = {  # type: ignore
                "$push": {"entries": {"$each": [], "$position": 0, "$slice": limit}}
            }

            updates["$set"] = {
                "expireAt": (
                    datetime.datetime.utcnow() + datetime.timedelta(seconds=expiry)
                )
            }
            updates["$push"]["entries"]["$each"] = [timestamp] * amount
            await self.database.windows.update_one(
                {
                    "_id": key,
                    "entries.%d"
                    % (limit - amount): {"$not": {"$gte": timestamp - expiry}},
                },
                updates,
                upsert=True,
            )

            return True
        except self.proxy_dependency.module.errors.DuplicateKeyError:
            return False
