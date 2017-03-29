import re
import inspect

from io import BytesIO, StringIO
from jinja2 import filters
from json import dumps
from flask import redirect
from werkzeug.routing import HTTPException, RoutingException
import six

import csv


def slugify(value):
    """Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.

    Copy/Pasted from ametaireau/pelican/utils itself took from django sources.
    """
    if isinstance(value, six.text_type):
        import unicodedata
        value = unicodedata.normalize('NFKD', value)
        if six.PY2:
            value = value.encode('ascii', 'ignore')
    value = six.text_type(re.sub('[^\w\s-]', '', value).strip().lower())
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

def list_of_dicts2json(dict_to_convert):
    """Take a list of dictionnaries and turns it into
    a json in-memory file
    """
    return BytesIO(dumps(dict_to_convert).encode('utf-8'))

def list_of_dicts2csv(dict_to_convert):
    """Take a list of dictionnaries and turns it into
    a csv in-memory file, assume all dict have the same keys
    """
    # CSV writer has a different behavior in PY2 and PY3
    # http://stackoverflow.com/a/37974772
    try:
        if six.PY3:
            csv_file = StringIO()
            # using list() for py3.4 compat. Otherwise, writerows() fails
            # (expecting a sequence getting a view)
            csv_data = [list(dict_to_convert[0].keys())]
            for dic in dict_to_convert:
                csv_data.append([dic[h] for h in dict_to_convert[0].keys()])
        else:
            csv_file = BytesIO()
            csv_data = []
            csv_data.append([key.encode('utf-8') for key in dict_to_convert[0].keys()])
            for dic in dict_to_convert:
                csv_data.append([dic[h].encode('utf8')
                                 if isinstance(dic[h], unicode) else str(dic[h]).encode('utf8')
                                 for h in dict_to_convert[0].keys()])
    except (KeyError, IndexError):
        csv_data = []
    writer = csv.writer(csv_file)
    writer.writerows(csv_data)
    csv_file.seek(0)
    if six.PY3:
        csv_file = BytesIO(csv_file.getvalue().encode('utf-8'))
    return csv_file
