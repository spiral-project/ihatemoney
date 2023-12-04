"""errors and exceptions."""

from flask.wrappers import Response
from werkzeug import exceptions

from .typing import Optional
from .wrappers import Limit


class RateLimitExceeded(exceptions.TooManyRequests):
    """Exception raised when a rate limit is hit."""

    def __init__(self, limit: Limit, response: Optional[Response] = None) -> None:
        """
        :param limit: The actual rate limit that was hit.
         Used to construct the default response message
        :param response: Optional pre constructed response. If provided
         it will be rendered by flask instead of the default error response
         of :class:`~werkzeug.exceptions.HTTPException`
        """
        self.limit = limit
        self.response = response
        if limit.error_message:
            description = (
                limit.error_message
                if not callable(limit.error_message)
                else limit.error_message()
            )
        else:
            description = str(limit.limit)
        super().__init__(description=description, response=response)
