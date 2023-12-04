"""
FlaskPlugin offers way of integrating Flask framework with
SQLAlchemy-Continuum. Flask-Plugin adds two columns for Transaction model,
namely `user_id` and `remote_addr`.

These columns are automatically populated when transaction object is created.
The `remote_addr` column is populated with the value of the remote address that
made current request. The `user_id` column is populated with the id of the
current_user object.

::

    from sqlalchemy_continuum.plugins import FlaskPlugin
    from sqlalchemy_continuum import make_versioned


    make_versioned(plugins=[FlaskPlugin()])
"""
from __future__ import absolute_import

flask = None
try:
    import flask
    from flask import request
    from flask.globals import _app_ctx_stack, _request_ctx_stack
except ImportError:
    pass
from sqlalchemy_utils import ImproperlyConfigured
from .base import Plugin


def fetch_current_user_id():
    from flask_login import current_user

    # Return None if we are outside of request context.
    if _app_ctx_stack.top is None or _request_ctx_stack.top is None:
        return
    try:
        return current_user.id
    except AttributeError:
        return


def fetch_remote_addr():
    # Return None if we are outside of request context.
    if _app_ctx_stack.top is None or _request_ctx_stack.top is None:
        return
    return request.remote_addr


class FlaskPlugin(Plugin):
    def __init__(
        self,
        current_user_id_factory=None,
        remote_addr_factory=None
    ):
        self.current_user_id_factory = (
            fetch_current_user_id if current_user_id_factory is None
            else current_user_id_factory
        )
        self.remote_addr_factory = (
            fetch_remote_addr if remote_addr_factory is None
            else remote_addr_factory
        )

        if not flask:
            raise ImproperlyConfigured(
                'Flask is required with FlaskPlugin. Please install Flask by'
                ' running pip install Flask'
            )

    def transaction_args(self, uow, session):
        return {
            'user_id': self.current_user_id_factory(),
            'remote_addr': self.remote_addr_factory()
        }
