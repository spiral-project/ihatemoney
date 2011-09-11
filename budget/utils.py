from functools import wraps
import inspect

from flask import redirect, url_for, session, request
from werkzeug.routing import HTTPException, RoutingException

from models import Bill, Project
from forms import BillForm

def get_billform_for(project, set_default=True):
    """Return an instance of BillForm configured for a particular project.

    :set_default: if set to True, on GET methods (usually when we want to 
                  display the default form, it will call set_default on it.
    
    """
    form = BillForm()
    form.payed_for.choices = form.payer.choices = [(str(m.id), m.name) for m in project.active_members]
    form.payed_for.default = [str(m.id) for m in project.active_members]

    if set_default and request.method == "GET":
        form.set_default()
    return form

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

