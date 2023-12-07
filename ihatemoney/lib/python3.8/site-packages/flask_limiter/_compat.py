from __future__ import annotations

import flask
from flask.ctx import RequestContext

# flask.globals.request_ctx is only available in Flask >= 2.2.0
try:
    from flask.globals import request_ctx
except ImportError:
    request_ctx = None


def request_context() -> RequestContext:
    if request_ctx is None:
        return flask._request_ctx_stack.top
    return request_ctx
