# -*- coding: utf-8 -*-
from flask import *
import werkzeug

from models import db, Project, Person, Bill
from utils import for_all_methods

from rest import RESTResource, need_auth # FIXME make it an ext


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


class ProjectHandler(object):

    def add(self):
        pass

    @need_auth(check_project, "project")
    def get(self, project):
        return "get"

    @need_auth(check_project, "project")
    def delete(self, project):
        return "delete"

    @need_auth(check_project, "project")
    def update(self, project):
        return "update"


class MemberHandler(object):

    def get(self, project, member_id):
        pass

    def list(self, project):
        return project.members

    def add(self, project):
        pass

    def update(self, project, member_id):
        pass

    def delete(self, project, member_id):
        pass


class BillHandler(object):

    def get(self, project, member_id):
        pass

    def list(self, project):
        pass

    def add(self, project):
        pass

    def update(self, project, member_id):
        pass

    def delete(self, project, member_id):
        pass


project_resource = RESTResource(
    name="project",
    route="/project", 
    app=api, 
    actions=["add", "update", "delete", "get"],
    handler=ProjectHandler())

member_resource = RESTResource(
    name="member",
    inject_name="project",
    route="/project/<project_id>/members",
    app=api,
    handler=MemberHandler(),
    authentifier=check_project)

bill_resource = RESTResource(
    name="bill",
    inject_name="project",
    route="/project/<project_id>/bills",
    app=api,
    handler=BillHandler(),
    authentifier=check_project)

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
