from __future__ import annotations

from abc import ABCMeta

from limits.typing import Dict, List, Tuple, Union

SCHEMES: Dict[str, StorageRegistry] = {}


class StorageRegistry(ABCMeta):
    def __new__(
        mcs, name: str, bases: Tuple[type, ...], dct: Dict[str, Union[str, List[str]]]
    ) -> StorageRegistry:
        storage_scheme = dct.get("STORAGE_SCHEME", None)
        cls = super().__new__(mcs, name, bases, dct)

        if storage_scheme:
            if isinstance(storage_scheme, str):  # noqa
                schemes = [storage_scheme]
            else:
                schemes = storage_scheme

            for scheme in schemes:
                SCHEMES[scheme] = cls

        return cls
