# -*- coding: utf-8 -*-
from flask import *
import werkzeug

from models import db, Project, Person, Bill
from utils import for_all_methods

from rest import RESTResource, DefaultHandler, need_auth # FIXME make it an ext


api = Blueprint("api", __name__, url_prefix="/api")

def check_project(*args, **kwargs):
    """Check the request for basic authentication for a given project.

    Return the project if the authorization is good, False otherwise
    """
    auth = request.authorization

    # project_id should be contained in kwargs and equal to the username
    if auth and "project_id" in kwargs and \
            auth.username == kwargs["project_id"]:
        project = Project.query.get(auth.username)
        if project.password == auth.password:
            return project
    return False


class ProjectHandler(DefaultHandler):

    def get(self, *args, **kwargs):
        return "get"

    def delete(self, *args, **kwargs):
        return "delete"

project_resource = RESTResource(
    name="project",
    route="/project", 
    app=api, 
    actions=["add", "update", "delete", "get"],
    authentifier=check_project,
    handler=ProjectHandler())

# projects: add, delete, edit, get
# GET /project/<id> → get
# PUT /project/<id> → add & edit
# DELETE /project/<id> → delete

# project members: list, add, delete
# GET /project/<id>/members → list
# POST /project/<id>/members/ → add
# PUT /project/<id>/members/<user_id> → edit
# DELETE /project/<id>/members/<user_id> → delete

# project bills: list, add, delete, edit, get
# GET /project/<id>/bills → list
# GET /project/<id>/bills/<bill_id> → get
# DELETE /project/<id>/bills/<bill_id> → delete
# POST /project/<id>/bills/ → add


# GET, PUT, DELETE: /<id> : Get, update and delete
# GET, POST: / Add & List
