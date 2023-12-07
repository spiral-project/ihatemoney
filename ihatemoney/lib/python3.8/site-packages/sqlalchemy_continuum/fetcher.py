import operator
import sqlalchemy as sa
from sqlalchemy_utils import get_primary_keys, identity
from .utils import tx_column_name, end_tx_column_name


def parent_identity(obj_or_class):
    return tuple(
        getattr(obj_or_class, column_key)
        for column_key in get_primary_keys(obj_or_class).keys()
        if column_key != tx_column_name(obj_or_class)
    )


def eqmap(callback, iterable):
    for a, b in zip(*map(callback, iterable)):
        yield a == b


def parent_criteria(obj, class_=None):
    if class_ is None:
        class_ = obj.__class__
    return eqmap(parent_identity, (class_, obj))


class VersionObjectFetcher(object):
    def __init__(self, manager):
        self.manager = manager

    def previous(self, obj):
        """
        Returns the previous version relative to this version in the version
        history. If current version is the first version this method returns
        None.
        """
        return self.previous_query(obj).first()

    def index(self, obj):
        """
        Return the index of this version in the version history.
        """
        session = sa.orm.object_session(obj)
        return session.execute(self._index_query(obj)).fetchone()[0]

    def next(self, obj):
        """
        Returns the next version relative to this version in the version
        history. If current version is the last version this method returns
        None.
        """
        return self.next_query(obj).first()

    def _transaction_id_subquery(self, obj, next_or_prev='next', alias=None):
        if next_or_prev == 'next':
            op = operator.gt
            func = sa.func.min
        else:
            op = operator.lt
            func = sa.func.max

        if alias is None:
            alias = sa.orm.aliased(obj.__class__)
            table = alias.__table__
            if hasattr(alias, 'c'):
                attrs = alias.c
            else:
                attrs = alias
        else:
            table = alias.original
            attrs = alias.c
        query = (
            sa.select(
                func(
                    getattr(attrs, tx_column_name(obj))
                )
            )
            .select_from(table)
            .where(
                sa.and_(
                    op(
                        getattr(attrs, tx_column_name(obj)),
                        getattr(obj, tx_column_name(obj))
                    ),
                    *[
                        getattr(attrs, pk) == getattr(obj, pk)
                        for pk in get_primary_keys(obj.__class__)
                        if pk != tx_column_name(obj)
                    ]
                )
            )
            .correlate(table)
        )
        return query.scalar_subquery()

    def _next_prev_query(self, obj, next_or_prev='next'):
        session = sa.orm.object_session(obj)

        subquery = self._transaction_id_subquery(
            obj, next_or_prev=next_or_prev
        )
        subquery = subquery.scalar_subquery()

        return (
            session.query(obj.__class__)
            .filter(
                sa.and_(
                    getattr(
                        obj.__class__,
                        tx_column_name(obj)
                    ) == subquery,
                    *parent_criteria(obj)
                )
            )
        )

    def _index_query(self, obj):
        """
        Returns the query needed for fetching the index of this record relative
        to version history.
        """
        alias = sa.orm.aliased(obj.__class__)

        subquery = (
            sa.select(sa.func.count()).select_from(alias.__table__)
            .where(
                getattr(alias, tx_column_name(obj))
                <
                getattr(obj, tx_column_name(obj))
            )
            .correlate(alias.__table__)
            .label('position')
        )
        query = (
            sa.select(subquery).select_from(obj.__table__)
            .where(
                sa.and_(*eqmap(identity, (obj.__class__, obj)))
            )
            .order_by(
                getattr(obj.__class__, tx_column_name(obj))
            )
        )
        return query


class SubqueryFetcher(VersionObjectFetcher):
    def previous_query(self, obj):
        """
        Returns the query that fetches the previous version relative to this
        version in the version history.
        """
        return self._next_prev_query(obj, 'previous')

    def next_query(self, obj):
        """
        Returns the query that fetches the next version relative to this
        version in the version history.
        """
        return self._next_prev_query(obj, 'next')


class ValidityFetcher(VersionObjectFetcher):
    def next_query(self, obj):
        """
        Returns the query that fetches the next version relative to this
        version in the version history.
        """
        session = sa.orm.object_session(obj)

        return (
            session.query(obj.__class__)
            .filter(
                sa.and_(
                    getattr(obj.__class__, tx_column_name(obj))
                    ==
                    getattr(obj, end_tx_column_name(obj)),
                    *parent_criteria(obj)
                )
            )
        )

    def previous_query(self, obj):
        """
        Returns the query that fetches the previous version relative to this
        version in the version history.
        """
        session = sa.orm.object_session(obj)

        return (
            session.query(obj.__class__)
            .filter(
                sa.and_(
                    getattr(obj.__class__, end_tx_column_name(obj))
                    ==
                    getattr(obj, tx_column_name(obj)),
                    *parent_criteria(obj)
                )
            )
        )
