import re
import inspect

from jinja2 import filters
from flask import redirect
from werkzeug.routing import HTTPException, RoutingException


def slugify(value):
    """Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.

    Copy/Pasted from ametaireau/pelican/utils itself took from django sources.
    """
    if type(value) == str:
        import unicodedata
        value = unicodedata.normalize('NFKD', value)
    value = re.sub('[^\w\s-]', '', value).strip().lower()
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


class PrefixedWSGI(object):
    '''
    Wrap the application in this middleware and configure the
    front-end server to add these headers, to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is
    different than what is used locally.

    It relies on "APPLICATION_ROOT" app setting.

    Inspired from http://flask.pocoo.org/snippets/35/

    :param app: the WSGI application
    '''
    def __init__(self, app):
        self.app = app
        self.wsgi_app = app.wsgi_app

    def __call__(self, environ, start_response):
        script_name = self.app.config['APPLICATION_ROOT']
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.wsgi_app(environ, start_response)


def minimal_round(*args, **kw):
    """ Jinja2 filter: rounds, but display only non-zero decimals

    from http://stackoverflow.com/questions/28458524/
    """
    # Use the original round filter, to deal with the extra arguments
    res = filters.do_round(*args, **kw)
    # Test if the result is equivalent to an integer and
    # return depending on it
    ires = int(res)
    return (res if res != ires else ires)
