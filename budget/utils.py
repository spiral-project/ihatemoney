import re
from functools import wraps
import inspect

from flask import redirect, url_for, session, request
from werkzeug.routing import HTTPException, RoutingException

def slugify(value):
    """Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.

    Copy/Pasted from ametaireau/pelican/utils itself took from django sources.
    """
    if type(value) == unicode:
        import unicodedata
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(re.sub('[^\w\s-]', '', value).strip().lower())
    return re.sub('[-\s]+', '-', value)

class Redirect303(HTTPException, RoutingException):
    """Raise if the map requests a redirect. This is for example the case if
    `strict_slashes` are activated and an url that requires a trailing slash.

    The attribute `new_url` contains the absolute destination url.
    """
    code = 303

    def __init__(self, new_url):
        RoutingException.__init__(self, new_url)
        self.new_url = new_url

    def get_response(self, environ):
        return redirect(self.new_url, 303)

def for_all_methods(decorator):
    """Apply a decorator to all the methods of a class"""
    def decorate(cls):
        for name, method in inspect.getmembers(cls, inspect.ismethod):
            setattr(cls, name, decorator(method))
        return cls
    return decorate

