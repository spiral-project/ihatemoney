from functools import wraps
from flask import redirect, url_for, session, request

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

def requires_auth(f):
    """Decorator checking that the user do have access to the given project id.

    If not, redirects to an authentication page, otherwise display the requested
    page.
    """

    @wraps(f)
    def decorator(*args, **kwargs):
        # if a project id is specified in kwargs, check we have access to it
        # get the password matching this project id
        # pop project_id out of the kwargs
        project_id = kwargs.pop('project_id')
        project = Project.query.get(project_id)
        if not project:
            return redirect(url_for("create_project", project_id=project_id))

        if project.id in session and session[project.id] == project.password:
            # add project into kwargs and call the original function
            kwargs['project'] = project
            return f(*args, **kwargs)
        else:
            # redirect to authentication page
            return redirect(url_for("authenticate",
                project_id=project.id, redirect_url=request.url))
    return decorator
