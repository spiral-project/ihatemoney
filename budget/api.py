# -*- coding: utf-8 -*-
from flask import *

from models import db, Project, Person, Bill
from utils import for_all_methods

from rest import RESTResource, need_auth# FIXME make it an ext
from werkzeug import Response


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
        return project

    @need_auth(check_project, "project")
    def delete(self, project):
        return "delete"

    @need_auth(check_project, "project")
    def update(self, project):
        return "update"


class MemberHandler(object):

    def get(self, project, member_id):
        member = Person.query.get(member_id)
        if not member or member.project != project:
            return Response('Not Found', status=404)
        return member

    def list(self, project):
        return project.members

    def add(self, project):
        pass

    def update(self, project, member_id):
        pass

    def delete(self, project, member_id):
        if project.remove_member(member_id):
            return Response('OK', status=200)


class BillHandler(object):

    def get(self, project, bill_id):
        bill = Bill.query.get(project, bill_id)
        if not bill:
            return Response('Not Found', status=404)
        return bill

    def list(self, project):
        return project.get_bills().all()

    def add(self, project):
        pass

    def update(self, project, bill_id):
        pass

    def delete(self, project, bill_id):
        bill = Bill.query.delete(project, bill_id)
        if not bill:
            return Response('Not Found', status=404)
        return bill


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
