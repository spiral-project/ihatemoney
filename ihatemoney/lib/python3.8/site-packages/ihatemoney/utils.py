import ast
import csv
import email.utils
from enum import Enum
from io import BytesIO, StringIO, TextIOWrapper
from json import JSONEncoder, dumps
import operator
import os
import re
import smtplib
import socket

from babel import Locale
from babel.numbers import get_currency_name, get_currency_symbol
from flask import current_app, flash, redirect, render_template
from flask_babel import get_locale, lazy_gettext as _
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import jinja2
from markupsafe import Markup, escape
from werkzeug.exceptions import HTTPException
from werkzeug.routing import RoutingException
from werkzeug.security import generate_password_hash as werkzeug_generate_password_hash

limiter = limiter = Limiter(
    current_app,
    key_func=get_remote_address,
    storage_uri="memory://",
)


def slugify(value):
    """Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    if isinstance(value, str):
        import unicodedata

        value = unicodedata.normalize("NFKD", value)
    value = str(re.sub(r"[^\w\s-]", "", value).strip().lower())
    return re.sub(r"[-\s]+", "-", value)


def send_email(mail_message):
    """Send an email using Flask-Mail, with proper error handling.

    Return True if everything went well, and False if there was an error.
    """
    # Since Python 3.4, SMTPException and socket.error are actually
    # identical, but this was not the case before.  Also, it is more clear
    # to check for both.
    try:
        current_app.mail.send(mail_message)
    except (smtplib.SMTPException, socket.error):
        return False
    # Email was sent successfully
    return True


def flash_email_error(error_message, category="danger"):
    """Helper to flash a message for email errors. It will also show the
    admin email as a contact if MAIL_DEFAULT_SENDER is set to not the
    default value and SHOW_ADMIN_EMAIL is True.
    """
    (admin_name, admin_email) = email.utils.parseaddr(
        current_app.config.get("MAIL_DEFAULT_SENDER")
    )
    error_extension = _("Please check the email configuration of the server.")
    if admin_email != "admin@example.com" and current_app.config.get(
        "SHOW_ADMIN_EMAIL"
    ):
        error_extension = _(
            "Please check the email configuration of the server "
            "or contact the administrator: %(admin_email)s",
            admin_email=admin_email,
        )

    flash(
        "{error_message} {error_extension}".format(
            error_message=error_message, error_extension=error_extension
        ),
        category=category,
    )


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
    """Jinja2 filter: rounds, but display only non-zero decimals

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
    return Locale.parse(iso_code)


def list_of_dicts2json(dict_to_convert):
    """Take a list of dictionnaries and turns it into
    a json in-memory file
    """
    return BytesIO(dumps(dict_to_convert).encode("utf-8"))


def escape_csv_formulae(value):
    # See https://owasp.org/www-community/attacks/CSV_Injection
    if (
        value
        and isinstance(value, str)
        and value[0] in ["=", "+", "-", "@", "\t", "\n"]
    ):
        return f"'{value}"
    return value


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
            csv_data.append(
                [escape_csv_formulae(dic[h]) for h in dict_to_convert[0].keys()]
            )
            # csv_data.append([dic[h] for h in dict_to_convert[0].keys()])
    except (KeyError, IndexError):
        csv_data = []
    writer = csv.writer(csv_file)
    writer.writerows(csv_data)
    csv_file.seek(0)
    csv_file = BytesIO(csv_file.getvalue().encode("utf-8"))
    return csv_file


def csv2list_of_dicts(csv_to_convert):
    """Take a csv in-memory file and turns it into
    a list of dictionnaries
    """
    csv_file = TextIOWrapper(csv_to_convert, encoding="utf-8")
    reader = csv.DictReader(csv_file)
    result = []
    for r in reader:
        """
        cospend embeds various data helping (cospend) imports
        'deleteMeIfYouWant' lines contains users
        'categoryname' table contains categories description
        we don't need them as we determine users and categories from bills
        """
        if r["what"] == "deleteMeIfYouWant":
            continue
        elif r["what"] == "categoryname":
            break
        r["amount"] = float(r["amount"])
        r["payer_weight"] = float(r["payer_weight"])
        r["owers"] = [o.strip() for o in r["owers"].split(",")]
        result.append(r)
    return result


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
                    return str(o)
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
    attr = ["what", "payer_name", "payer_weight", "amount", "currency", "date", "owers"]
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
        return rf'<em class="font-italic">{string}<\/em>'
    else:
        return f'<em class="font-italic">{string}</em>'


def localize_list(items, surround_with_em=True):
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

    if len(items) == 0:
        return ""

    item_wrapper = em_surround if surround_with_em else lambda x: x
    wrapped_items = list(map(item_wrapper, items))

    if len(wrapped_items) == 1:
        return str(wrapped_items[0])
    elif len(wrapped_items) == 2:
        # I18N: List with two items only
        return _("{dual_object_0} and {dual_object_1}").format(
            dual_object_0=wrapped_items[0], dual_object_1=wrapped_items[1]
        )
    else:
        # I18N: Last two items of a list with more than 3 items
        output_str = _("{previous_object}, and {end_object}").format(
            previous_object="{previous_object}", end_object=wrapped_items.pop()
        )
        # I18N: Two items in a middle of a list with more than 5 objects
        middle = _("{previous_object}, {next_object}")
        while len(wrapped_items) > 2:
            temp = middle.format(
                previous_object="{previous_object}",
                next_object=wrapped_items.pop(),
            )
            output_str = output_str.format(previous_object=temp)

        output_str = output_str.format(previous_object=wrapped_items.pop())
        # I18N: First two items of a list with more than 3 items
        output_str = _("{start_object}, {next_object}").format(
            start_object="{start_object}", next_object=output_str
        )
        return output_str.format(start_object=wrapped_items.pop())


def render_localized_currency(code, detailed=True):
    # We cannot use CurrencyConvertor.no_currency here because of circular dependencies
    if code == "XXX":
        return _("No Currency")
    locale = get_locale() or "en_US"
    symbol = get_currency_symbol(code, locale=locale)
    details = ""
    if detailed:
        details = f" − {get_currency_name(code, locale=locale)}"
    if symbol == code:
        return f"{code}{details}"
    else:
        return f"{code} − {symbol}{details}"


def render_localized_template(template_name_prefix, **context):
    """Like render_template(), but selects the right template according to the
    current user language.  Fallback to English if a template for the
    current language does not exist.
    """
    fallback = "en"
    templates = [
        f"{template_name_prefix}.{lang}.j2"
        for lang in (get_locale().language, fallback)
    ]
    # render_template() supports a list of templates to try in order
    return render_template(templates, **context)


def format_form_errors(form, prefix):
    """Format all form errors into a single string, with a string prefix in
    front.  Useful for flashing the result.
    """
    if len(form.errors) == 0:
        return ""
    elif len(form.errors) == 1:
        # I18N: Form error with only one error
        return _("{prefix}: {error}").format(
            prefix=prefix, error=form.errors.popitem()[1][0]
        )
    else:
        error_list = "</li><li>".join(
            str(error) for (field, errors) in form.errors.items() for error in errors
        )
        errors = f"<ul><li>{error_list}</li></ul>"
        # I18N: Form error with a list of errors
        return Markup(_("{prefix}:<br />{errors}").format(prefix=prefix, errors=errors))


def generate_password_hash(*args, **kwargs):
    if current_app.config.get("PASSWORD_HASH_METHOD"):
        kwargs.setdefault("method", current_app.config["PASSWORD_HASH_METHOD"])

    if current_app.config.get("PASSWORD_HASH_SALT_LENGTH"):
        kwargs.setdefault(
            "salt_length", current_app.config["PASSWORD_HASH_SALT_LENGTH"]
        )

    return werkzeug_generate_password_hash(*args, **kwargs)
