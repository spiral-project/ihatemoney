import sqlalchemy as sa

from .reverter import Reverter
from .utils import get_versioning_manager, is_internal_column, parent_class


class VersionClassBase(object):
    @property
    def previous(self):
        """
        Returns the previous version relative to this version in the version
        history. If current version is the first version this method returns
        None.
        """
        return (
            get_versioning_manager(self)
            .fetcher(parent_class(self.__class__))
            .previous(self)
        )

    @property
    def next(self):
        """
        Returns the next version relative to this version in the version
        history. If current version is the last version this method returns
        None.
        """
        return (
            get_versioning_manager(self)
            .fetcher(parent_class(self.__class__))
            .next(self)
        )

    @property
    def index(self):
        """
        Return the index of this version in the version history.
        """
        return (
            get_versioning_manager(self)
            .fetcher(parent_class(self.__class__))
            .index(self)
        )

    @property
    def changeset(self):
        """
        Return a dictionary of changed fields in this version with keys as
        field names and values as lists with first value as the old field value
        and second list value as the new value.
        """
        previous_version = self.previous
        data = {}

        for key in sa.inspect(self.__class__).columns.keys():
            if is_internal_column(self, key):
                continue
            if not previous_version:
                old = None
            else:
                old = getattr(previous_version, key)
            new = getattr(self, key)
            if old != new:
                data[key] = [old, new]

        manager = get_versioning_manager(self)
        manager.plugins.after_construct_changeset(self, data)
        return data

    def revert(self, relations=[]):
        return Reverter(self, relations=relations)()
