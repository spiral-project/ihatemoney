from collections import OrderedDict

import six
import sqlalchemy as sa
from sqlalchemy_continuum import __version__ as continuum_version
from sqlalchemy_continuum.exc import ImproperlyConfigured
from sqlalchemy_continuum.transaction import (
    TransactionBase,
    TransactionFactory,
    create_triggers,
)

if continuum_version != "1.3.14":
    import warnings

    warnings.warn(
        "SQLAlchemy-continuum version changed. Please check monkeypatching usefulness."
    )


class PatchedTransactionFactory(TransactionFactory):
    """
    Monkeypatching TransactionFactory for
    https://github.com/kvesteri/sqlalchemy-continuum/issues/264
    There is no easy way to really remove Sequence without redefining the whole method. So,
    this is a copy/paste. :/
    """

    def create_class(self, manager):
        """
        Create Transaction class.
        """

        class Transaction(manager.declarative_base, TransactionBase):
            __tablename__ = "transaction"
            __versioning_manager__ = manager

            id = sa.Column(
                sa.types.BigInteger,
                # sa.schema.Sequence('transaction_id_seq'),
                primary_key=True,
                autoincrement=True,
            )

            if self.remote_addr:
                remote_addr = sa.Column(sa.String(50))

            if manager.user_cls:
                user_cls = manager.user_cls
                Base = manager.declarative_base
                try:
                    registry = Base.registry._class_registry
                except AttributeError:  # SQLAlchemy < 1.4
                    registry = Base._decl_class_registry

                if isinstance(user_cls, six.string_types):
                    try:
                        user_cls = registry[user_cls]
                    except KeyError:
                        raise ImproperlyConfigured(
                            "Could not build relationship between Transaction"
                            " and %s. %s was not found in declarative class "
                            "registry. Either configure VersioningManager to "
                            "use different user class or disable this "
                            "relationship " % (user_cls, user_cls)
                        )

                user_id = sa.Column(
                    sa.inspect(user_cls).primary_key[0].type,
                    sa.ForeignKey(sa.inspect(user_cls).primary_key[0]),
                    index=True,
                )

                user = sa.orm.relationship(user_cls)

            def __repr__(self):
                fields = ["id", "issued_at", "user"]
                field_values = OrderedDict(
                    (field, getattr(self, field))
                    for field in fields
                    if hasattr(self, field)
                )
                return "<Transaction %s>" % ", ".join(
                    (
                        "%s=%r" % (field, value)
                        if not isinstance(value, six.integer_types)
                        # We want the following line to ensure that longs get
                        # shown without the ugly L suffix on python 2.x
                        # versions
                        else "%s=%d" % (field, value)
                        for field, value in field_values.items()
                    )
                )

        if manager.options["native_versioning"]:
            create_triggers(Transaction)
        return Transaction
