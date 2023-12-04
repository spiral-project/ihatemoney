import sqlalchemy as sa
from .exc import ClassNotVersioned, ImproperlyConfigured
from .manager import VersioningManager
from .operation import Operation
from .transaction import TransactionFactory
from .unit_of_work import UnitOfWork
from .utils import (
    changeset,
    count_versions,
    get_versioning_manager,
    is_modified,
    is_session_modified,
    parent_class,
    transaction_class,
    tx_column_name,
    vacuum,
    version_class,
)


__version__ = '1.4.0'


versioning_manager = VersioningManager()


def make_versioned(
    mapper=sa.orm.Mapper,
    session=sa.orm.session.Session,
    manager=versioning_manager,
    plugins=None,
    options=None,
    user_cls='User'
):
    """
    This is the public API function of SQLAlchemy-Continuum for making certain
    mappers and sessions versioned. By default this applies to all mappers and
    all sessions.

    :param mapper:
        SQLAlchemy mapper to apply the versioning to.
    :param session:
        SQLAlchemy session to apply the versioning to. By default this is
        sa.orm.session.Session meaning it applies to all Session subclasses.
    :param manager:
        SQLAlchemy-Continuum versioning manager.
    :param plugins:
        Plugins to pass for versioning manager.
    :param options:
        A dictionary of VersioningManager options.
    :param user_cls:
        User class which the Transaction class should have relationship to.
        This can either be a class or string name of a class for lazy
        evaluation.
    """
    if plugins is not None:
        manager.plugins = plugins

    if options is not None:
        manager.options.update(options)

    manager.user_cls = user_cls
    manager.apply_class_configuration_listeners(mapper)
    manager.track_operations(mapper)
    manager.track_session(session)

    sa.event.listen(
        sa.engine.Engine,
        'before_execute',
        manager.track_association_operations
    )

    sa.event.listen(
        sa.engine.Engine,
        'rollback',
        manager.clear_connection
    )

    sa.event.listen(
        sa.engine.Engine,
        'set_connection_execution_options',
        manager.track_cloned_connections
    )


def remove_versioning(
    mapper=sa.orm.Mapper,
    session=sa.orm.session.Session,
    manager=versioning_manager
):
    """
    Remove the versioning from given mapper / session and manager.

    :param mapper:
        SQLAlchemy mapper to remove the versioning from.
    :param session:
        SQLAlchemy session to remove the versioning from. By default this is
        sa.orm.session.Session meaning it applies to all sessions.
    :param manager:
        SQLAlchemy-Continuum versioning manager.
    """
    manager.reset()
    manager.remove_class_configuration_listeners(mapper)
    manager.remove_operations_tracking(mapper)
    manager.remove_session_tracking(session)
    sa.event.remove(
        sa.engine.Engine,
        'before_execute',
        manager.track_association_operations
    )

    sa.event.remove(
        sa.engine.Engine,
        'rollback',
        manager.clear_connection
    )

    sa.event.remove(
        sa.engine.Engine,
        'set_connection_execution_options',
        manager.track_cloned_connections
    )
