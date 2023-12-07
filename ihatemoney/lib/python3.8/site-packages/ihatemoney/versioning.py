from flask import g
from sqlalchemy.orm.attributes import get_history
from sqlalchemy_continuum import VersioningManager
from sqlalchemy_continuum.plugins.flask import fetch_remote_addr

from ihatemoney.utils import FormEnum


class LoggingMode(FormEnum):
    """Represents a project's history preferences."""

    DISABLED = 0
    ENABLED = 1
    RECORD_IP = 2

    @classmethod
    def default(cls):
        return cls.ENABLED


class ConditionalVersioningManager(VersioningManager):
    """Conditionally enable version tracking based on the given predicate."""

    def __init__(self, tracking_predicate, *args, **kwargs):
        """Create version entry iff tracking_predicate() returns True."""
        super().__init__(*args, **kwargs)
        self.tracking_predicate = tracking_predicate

    def before_flush(self, session, flush_context, instances):
        if self.tracking_predicate():
            return super().before_flush(session, flush_context, instances)
        else:
            # At least one call to unit_of_work() needs to be made against the
            # session object to prevent a KeyError later. This doesn't create
            # a version or transaction entry
            self.unit_of_work(session)

    def after_flush(self, session, flush_context):
        if self.tracking_predicate():
            return super().after_flush(session, flush_context)
        else:
            # At least one call to unit_of_work() needs to be made against the
            # session object to prevent a KeyError later. This doesn't create
            # a version or transaction entry
            self.unit_of_work(session)


def version_privacy_predicate():
    """Evaluate if the project of the current session has enabled logging."""
    logging_enabled = False
    try:
        if g.project.logging_preference != LoggingMode.DISABLED:
            logging_enabled = True

        # If logging WAS enabled prior to this transaction,
        # we log this one last transaction
        old_logging_mode = get_history(g.project, "logging_preference")[2]
        if old_logging_mode and old_logging_mode[0] != LoggingMode.DISABLED:
            logging_enabled = True
    except AttributeError:
        # g.project doesn't exist, it's being created or this action is outside
        # the scope of a project. Use the default logging mode to decide
        if LoggingMode.default() != LoggingMode.DISABLED:
            logging_enabled = True
    return logging_enabled


def get_ip_if_allowed():
    """
    Get the remote address (IP address) of the current Flask context, if the
    project's privacy settings allow it. Behind the scenes, this calls back to
    the FlaskPlugin from SQLAlchemy-Continuum in order to maintain forward
    compatibility
    """
    ip_logging_allowed = False
    try:
        if g.project.logging_preference == LoggingMode.RECORD_IP:
            ip_logging_allowed = True

        # If ip recording WAS enabled prior to this transaction,
        # we record the IP for this one last transaction
        old_logging_mode = get_history(g.project, "logging_preference")[2]
        if old_logging_mode and old_logging_mode[0] == LoggingMode.RECORD_IP:
            ip_logging_allowed = True
    except AttributeError:
        # g.project doesn't exist, it's being created or this action is outside
        # the scope of a project. Use the default logging mode to decide
        if LoggingMode.default() == LoggingMode.RECORD_IP:
            ip_logging_allowed = True

    if ip_logging_allowed:
        return fetch_remote_addr()
    else:
        return None
