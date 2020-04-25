import ast
import csv
from datetime import datetime, timedelta
from enum import Enum
from io import BytesIO, StringIO
from json import JSONEncoder, dumps
import operator
import os
import re

from babel import Locale
from flask import current_app, escape, redirect
from flask_babel import gettext as _
import jinja2
from werkzeug.routing import HTTPException, RoutingException


def slugify(value):
    """Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    if isinstance(value, str):
        import unicodedata

        value = unicodedata.normalize("NFKD", value)
    value = str(re.sub(r"[^\w\s-]", "", value).strip().lower())
    return re.sub(r"[-\s]+", "-", value)


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

    """
    Wrap the application in this middleware and configure the
    front-end server to add these headers, to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is
    different than what is used locally.

    It relies on "APPLICATION_ROOT" app setting.

    Inspired from http://flask.pocoo.org/snippets/35/

    :param app: the WSGI application
    """

    def __init__(self, app):
        self.app = app
        self.wsgi_app = app.wsgi_app

    def __call__(self, environ, start_response):
        script_name = self.app.config["APPLICATION_ROOT"]
        if script_name:
            environ["SCRIPT_NAME"] = script_name
            path_info = environ["PATH_INFO"]
            if path_info.startswith(script_name):
                environ["PATH_INFO"] = path_info[len(script_name) :]  # NOQA

        scheme = environ.get("HTTP_X_SCHEME", "")
        if scheme:
            environ["wsgi.url_scheme"] = scheme
        return self.wsgi_app(environ, start_response)


def minimal_round(*args, **kw):
    """ Jinja2 filter: rounds, but display only non-zero decimals

    from http://stackoverflow.com/questions/28458524/
    """
    # Use the original round filter, to deal with the extra arguments
    res = jinja2.filters.do_round(*args, **kw)
    # Test if the result is equivalent to an integer and
    # return depending on it
    ires = int(res)
    return res if res != ires else ires


def static_include(filename):
    fullpath = os.path.join(current_app.static_folder, filename)
    with open(fullpath, "r") as f:
        return f.read()


def locale_from_iso(iso_code):
    return Locale(iso_code)


def list_of_dicts2json(dict_to_convert):
    """Take a list of dictionnaries and turns it into
    a json in-memory file
    """
    return BytesIO(dumps(dict_to_convert).encode("utf-8"))


def list_of_dicts2csv(dict_to_convert):
    """Take a list of dictionnaries and turns it into
    a csv in-memory file, assume all dict have the same keys
    """
    # CSV writer has a different behavior in PY2 and PY3
    # http://stackoverflow.com/a/37974772
    try:
        csv_file = StringIO()
        # using list() for py3.4 compat. Otherwise, writerows() fails
        # (expecting a sequence getting a view)
        csv_data = [list(dict_to_convert[0].keys())]
        for dic in dict_to_convert:
            csv_data.append([dic[h] for h in dict_to_convert[0].keys()])
    except (KeyError, IndexError):
        csv_data = []
    writer = csv.writer(csv_file)
    writer.writerows(csv_data)
    csv_file.seek(0)
    csv_file = BytesIO(csv_file.getvalue().encode("utf-8"))
    return csv_file


class LoginThrottler:
    """Simple login throttler used to limit authentication attempts based on client's ip address.
    When using multiple workers, remaining number of attempts can get inconsistent
    but will still be limited to num_workers * max_attempts.
    """

    def __init__(self, max_attempts=3, delay=1):
        self._max_attempts = max_attempts
        # Delay in minutes before resetting the attempts counter
        self._delay = delay
        self._attempts = {}

    def get_remaining_attempts(self, ip):
        return self._max_attempts - self._attempts.get(ip, [datetime.now(), 0])[1]

    def increment_attempts_counter(self, ip):
        # Reset all attempt counters when they get hungry for memory
        if len(self._attempts) > 10000:
            self.__init__()
        if self._attempts.get(ip) is None:
            # Store first attempt date and number of attempts since
            self._attempts[ip] = [datetime.now(), 0]
        self._attempts.get(ip)[1] += 1

    def is_login_allowed(self, ip):
        if self._attempts.get(ip) is None:
            return True
        # When the delay is expired, reset the counter
        if datetime.now() - self._attempts.get(ip)[0] > timedelta(minutes=self._delay):
            self.reset(ip)
            return True
        if self._attempts.get(ip)[1] >= self._max_attempts:
            return False
        return True

    def reset(self, ip):
        self._attempts.pop(ip, None)


def create_jinja_env(folder, strict_rendering=False):
    """Creates and return a Jinja2 Environment object, used, to load the
    templates.

    :param strict_rendering:
        if set to `True`, all templates which use an undefined variable will
        throw an exception (default to `False`).
    """
    loader = jinja2.PackageLoader("ihatemoney", folder)
    kwargs = {"loader": loader}
    if strict_rendering:
        kwargs["undefined"] = jinja2.StrictUndefined
    return jinja2.Environment(**kwargs)


class IhmJSONEncoder(JSONEncoder):
    """Subclass of the default encoder to support custom objects.
    Taken from the deprecated flask-rest package."""

    def default(self, o):
        if hasattr(o, "_to_serialize"):
            return o._to_serialize
        elif hasattr(o, "isoformat"):
            return o.isoformat()
        else:
            try:
                from flask_babel import speaklater

                if isinstance(o, speaklater.LazyString):
                    try:
                        return unicode(o)  # For python 2.
                    except NameError:
                        return str(o)  # For python 3.
            except ImportError:
                pass
            return JSONEncoder.default(self, o)


def eval_arithmetic_expression(expr):
    def _eval(node):
        # supported operators
        operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.USub: operator.neg,
        }

        if isinstance(node, ast.Num):  # <number>
            return node.n
        elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
            return operators[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):  # <operator> <operand> e.g., -1
            return operators[type(node.op)](_eval(node.operand))
        else:
            raise TypeError(node)

    expr = str(expr)

    try:
        result = _eval(ast.parse(expr, mode="eval").body)
    except (SyntaxError, TypeError, ZeroDivisionError, KeyError):
        raise ValueError("Error evaluating expression: {}".format(expr))

    return result


def get_members(file):
    members_list = list()
    for item in file:
        if (item["payer_name"], item["payer_weight"]) not in members_list:
            members_list.append((item["payer_name"], item["payer_weight"]))
    for item in file:
        for ower in item["owers"]:
            if ower not in [i[0] for i in members_list]:
                members_list.append((ower, 1))

    return members_list


def same_bill(bill1, bill2):
    attr = ["what", "payer_name", "payer_weight", "amount", "date", "owers"]
    for a in attr:
        if bill1[a] != bill2[a]:
            return False
    return True


class FormEnum(Enum):
    """Extend builtin Enum class to be seamlessly compatible with WTForms"""

    @classmethod
    def choices(cls):
        return [(choice, choice.name) for choice in cls]

    @classmethod
    def coerce(cls, item):
        """Coerce a str or int representation into an Enum object"""
        if isinstance(item, cls):
            return item

        # If item is not already a Enum object then it must be
        # a string or int corresponding to an ID (e.g. '0' or 1)
        # Either int() or cls() will correctly throw a TypeError if this
        # is not the case
        return cls(int(item))

    def __str__(self):
        return str(self.value)


def em_surround(string, regex_escape=False):
    # Needed since we're going to assume this is safe later in order to render
    # the <em> tag we're adding
    string = escape(string)

    if regex_escape:
        return r'<em class="font-italic">%s<\/em>' % string
    else:
        return '<em class="font-italic">%s</em>' % string


def localize_list(list, surround_with_em=True):
    """
    Localize a list, optionally surrounding each item in <em> tags.

    Uses the appropriate joining character, oxford comma behavior, and handles
    1, and 2 object lists, all according to localizable behavior.

    Examples (using en locale):
        >>> localize_list([1,2,3,4,5], False)
        1, 2, 3, 4, and 5

        >>> localize_list([1,2], False)
        1 and 2

    Based on the LUA example from:
    https://stackoverflow.com/a/58033018

    :param list: The list of objects to localize by a call to str()
    :param surround_with_em: Optionally surround each object with <em> tags
    :return: A locally formatted list of objects
    """
    list = list[:]
    one = _("{single_object}")
    two = _("{dual_object_0} and {dual_object_1}")
    start = _("{start_object}, {next_object}")
    middle = _("{previous_object}, {next_object}")
    end = _("{previous_object}, and {end_object}")

    item_wrapper = em_surround
    # fmt: off
    if not surround_with_em:
        def item_wrapper(x):
            return x
    # fmt: on

    if len(list) == 1:
        return one.format(single_object=item_wrapper(list[0]))
    elif len(list) == 2:
        return two.format(
            dual_object_0=item_wrapper(list[0]), dual_object_1=item_wrapper(list[1])
        )
    else:
        output_str = end.format(
            previous_object="{previous_object}", end_object=item_wrapper(list.pop())
        )
        while len(list) > 2:
            temp = middle.format(
                previous_object="{previous_object}",
                next_object=item_wrapper(list.pop()),
            )
            output_str = output_str.format(previous_object=temp)

        output_str = output_str.format(previous_object=item_wrapper(list.pop()))
        output_str = start.format(start_object="{start_object}", next_object=output_str)
        return output_str.format(start_object=item_wrapper(list.pop()))
