import threading
import time
from collections import Counter

import limits.typing
from limits.storage.base import MovingWindowSupport, Storage
from limits.typing import Dict, List, Optional, Tuple


class LockableEntry(threading._RLock):  # type: ignore
    def __init__(self, expiry: float) -> None:
        self.atime = time.time()
        self.expiry = self.atime + expiry
        super().__init__()


class MemoryStorage(Storage, MovingWindowSupport):
    """
    rate limit storage using :class:`collections.Counter`
    as an in memory storage for fixed and elastic window strategies,
    and a simple list to implement moving window strategy.

    """

    STORAGE_SCHEME = ["memory"]

    def __init__(self, uri: Optional[str] = None, **_: str):
        self.storage: limits.typing.Counter[str] = Counter()
        self.expirations: Dict[str, float] = {}
        self.events: Dict[str, List[LockableEntry]] = {}
        self.timer = threading.Timer(0.01, self.__expire_events)
        self.timer.start()
        super().__init__(uri, **_)

    def __expire_events(self) -> None:
        for key in list(self.events.keys()):
            for event in list(self.events[key]):
                with event:
                    if event.expiry <= time.time() and event in self.events[key]:
                        self.events[key].remove(event)

        for key in list(self.expirations.keys()):
            if self.expirations[key] <= time.time():
                self.storage.pop(key, None)
                self.expirations.pop(key, None)

    def __schedule_expiry(self) -> None:
        if not self.timer.is_alive():
            self.timer = threading.Timer(0.01, self.__expire_events)
            self.timer.start()

    def incr(
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
        self.get(key)
        self.__schedule_expiry()
        self.storage[key] += amount

        if elastic_expiry or self.storage[key] == amount:
            self.expirations[key] = time.time() + expiry

        return self.storage.get(key, 0)

    def get(self, key: str) -> int:
        """
        :param key: the key to get the counter value for
        """

        if self.expirations.get(key, 0) <= time.time():
            self.storage.pop(key, None)
            self.expirations.pop(key, None)

        return self.storage.get(key, 0)

    def clear(self, key: str) -> None:
        """
        :param key: the key to clear rate limits for
        """
        self.storage.pop(key, None)
        self.expirations.pop(key, None)
        self.events.pop(key, None)

    def acquire_entry(self, key: str, limit: int, expiry: int, amount: int = 1) -> bool:
        """
        :param key: rate limit key to acquire an entry in
        :param limit: amount of entries allowed
        :param expiry: expiry of the entry
        :param amount: the number of entries to acquire
        """
        if amount > limit:
            return False

        self.events.setdefault(key, [])
        self.__schedule_expiry()
        timestamp = time.time()
        try:
            entry = self.events[key][limit - amount]
        except IndexError:
            entry = None

        if entry and entry.atime >= timestamp - expiry:
            return False
        else:
            self.events[key][:0] = [LockableEntry(expiry) for _ in range(amount)]
            return True

    def get_expiry(self, key: str) -> int:
        """
        :param key: the key to get the expiry for
        """

        return int(self.expirations.get(key, time.time()))

    def get_num_acquired(self, key: str, expiry: int) -> int:
        """
        returns the number of entries already acquired

        :param key: rate limit key to acquire an entry in
        :param expiry: expiry of the entry
        """
        timestamp = time.time()

        return (
            len([k for k in self.events[key] if k.atime >= timestamp - expiry])
            if self.events.get(key)
            else 0
        )

    def get_moving_window(self, key: str, limit: int, expiry: int) -> Tuple[int, int]:
        """
        returns the starting point and the number of entries in the moving
        window

        :param key: rate limit key
        :param expiry: expiry of entry
        :return: (start of window, number of acquired entries)
        """
        timestamp = time.time()
        acquired = self.get_num_acquired(key, expiry)

        for item in self.events.get(key, []):
            if item.atime >= timestamp - expiry:
                return int(item.atime), acquired

        return int(timestamp), acquired

    def check(self) -> bool:
        """
        check if storage is healthy
        """

        return True

    def reset(self) -> Optional[int]:
        num_items = max(len(self.storage), len(self.events))
        self.storage.clear()
        self.expirations.clear()
        self.events.clear()
        return num_items
