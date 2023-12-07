"""

"""
import dataclasses
import re
import sys
from collections import UserDict
from types import ModuleType
from typing import TYPE_CHECKING, cast

import importlib_resources
from packaging.version import Version

from limits.typing import Dict, List, NamedTuple, Optional, Tuple, Type, Union

from .errors import ConfigurationError
from .limits import GRANULARITIES, RateLimitItem

SEPARATORS = re.compile(r"[,;|]{1}")
SINGLE_EXPR = re.compile(
    r"""
    \s*([0-9]+)
    \s*(/|\s*per\s*)
    \s*([0-9]+)
    *\s*(hour|minute|second|day|month|year)s?\s*""",
    re.IGNORECASE | re.VERBOSE,
)
EXPR = re.compile(
    r"^{SINGLE}(:?{SEPARATORS}{SINGLE})*$".format(
        SINGLE=SINGLE_EXPR.pattern, SEPARATORS=SEPARATORS.pattern
    ),
    re.IGNORECASE | re.VERBOSE,
)


class WindowStats(NamedTuple):
    """
    Tuple to describe a rate limited window
    """

    #: Time as seconds since the Epoch when this window will be reset
    reset_time: int
    #: Quantity remaining in this window
    remaining: int


@dataclasses.dataclass
class Dependency:
    name: str
    version_required: Optional[Version]
    version_found: Optional[Version]
    module: ModuleType


if TYPE_CHECKING:
    _UserDict = UserDict[str, Dependency]
else:
    _UserDict = UserDict


class DependencyDict(_UserDict):
    Missing = Dependency("Missing", None, None, ModuleType("Missing"))

    def __getitem__(self, key: str) -> Dependency:
        dependency = super().__getitem__(key)

        if dependency == DependencyDict.Missing:
            raise ConfigurationError(f"{key} prerequisite not available")
        elif dependency.version_required and (
            not dependency.version_found
            or dependency.version_found < dependency.version_required
        ):
            raise ConfigurationError(
                f"The minimum version of {dependency.version_required}"
                f" of {dependency.name} could not be found"
            )

        return dependency


class LazyDependency:
    """
    Simple utility that provides an :attr:`dependency`
    to the child class to fetch any dependencies
    without having to import them explicitly.
    """

    DEPENDENCIES: Union[Dict[str, Optional[Version]], List[str]] = []
    """
    The python modules this class has a dependency on.
    Used to lazily populate the :attr:`dependencies`
    """

    def __init__(self) -> None:
        self._dependencies: DependencyDict = DependencyDict()

    @property
    def dependencies(self) -> DependencyDict:
        """
        Cached mapping of the modules this storage depends on.
        This is done so that the module is only imported lazily
        when the storage is instantiated.

        :meta private:
        """

        if not getattr(self, "_dependencies", None):
            dependencies = DependencyDict()
            mapping: Dict[str, Optional[Version]]

            if isinstance(self.DEPENDENCIES, list):
                mapping = {dependency: None for dependency in self.DEPENDENCIES}
            else:
                mapping = self.DEPENDENCIES

            for name, minimum_version in mapping.items():
                dependency, version = get_dependency(name)

                if not dependency:
                    dependencies[name] = DependencyDict.Missing
                else:
                    dependencies[name] = Dependency(
                        name, minimum_version, version, dependency
                    )
            self._dependencies = dependencies

        return self._dependencies


def get_dependency(module_path: str) -> Tuple[Optional[ModuleType], Optional[Version]]:
    """
    safe function to import a module at runtime
    """
    try:
        if module_path not in sys.modules:
            __import__(module_path)
        root = module_path.split(".")[0]
        version = getattr(sys.modules[root], "__version__", "0.0.0")

        return sys.modules[module_path], Version(version)
    except ImportError:  # pragma: no cover
        return None, None


def get_package_data(path: str) -> bytes:
    return cast(bytes, importlib_resources.files("limits").joinpath(path).read_bytes())


def parse_many(limit_string: str) -> List[RateLimitItem]:
    """
    parses rate limits in string notation containing multiple rate limits
    (e.g. ``1/second; 5/minute``)

    :param limit_string: rate limit string using :ref:`ratelimit-string`
    :raise ValueError: if the string notation is invalid.

    """

    if not (isinstance(limit_string, str) and EXPR.match(limit_string)):
        raise ValueError("couldn't parse rate limit string '%s'" % limit_string)
    limits = []

    for limit in SEPARATORS.split(limit_string):
        match = SINGLE_EXPR.match(limit)

        if match:
            amount, _, multiples, granularity_string = match.groups()
            granularity = granularity_from_string(granularity_string)
            limits.append(
                granularity(int(amount), multiples and int(multiples) or None)
            )

    return limits


def parse(limit_string: str) -> RateLimitItem:
    """
    parses a single rate limit in string notation
    (e.g. ``1/second`` or ``1 per second``)

    :param limit_string: rate limit string using :ref:`ratelimit-string`
    :raise ValueError: if the string notation is invalid.

    """

    return list(parse_many(limit_string))[0]


def granularity_from_string(granularity_string: str) -> Type[RateLimitItem]:
    """

    :param granularity_string:
    :raise ValueError:
    """

    for granularity in GRANULARITIES.values():
        if granularity.check_granularity_string(granularity_string):
            return granularity
    raise ValueError("no granularity matched for %s" % granularity_string)
