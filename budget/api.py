# -*- coding: utf-8 -*-
from flask import *

from models import db, Project, Person, Bill
from forms import ProjectForm
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
        if project and project.password == auth.password:
            return project
    return False


class ProjectHandler(object):

    def add(self):
        form = ProjectForm(csrf_enabled=False)
        if form.validate():
            project = form.save(Project())
            db.session.add(project)
            db.session.commit()
            return 201, project.id
        return 400, form.errors

    @need_auth(check_project, "project")
    def get(self, project):
        return project

    @need_auth(check_project, "project")
    def delete(self, project):
        db.session.delete(project)
        db.session.commit()
        return 200, "DELETED"

    @need_auth(check_project, "project")
    def update(self, project):
        form = ProjectForm(csrf_enabled=False)
        if form.validate():
            form.save(project)
            db.session.commit()
            return 200, "UPDATED"
        return 400, form.errors


class MemberHandler(object):

    def get(self, project, member_id):
        member = Person.query.get(member_id)
        if not member or member.project != project:
            return 404, "Not Found"
        return member

    def list(self, project):
        return project.members

    def add(self, project):
        form = MemberForm(csrf_enabled=False)
        if form.validate():
            member = Person()
            form.save(project, member)
            db.session.commit()
            return 200, member.id
        return 400, form.errors

    def update(self, project, member_id):
        form = MemberForm(csrf_enabled=False)
        if form.validate():
            member = Person.query.get(member_id, project)
            form.save(project, member)
            db.session.commit()
            return 200, member
        return 400, form.errors

    def delete(self, project, member_id):
        if project.remove_member(member_id):
            return 200, "OK"
        return 404, "Not Found"


class BillHandler(object):

    def get(self, project, bill_id):
        bill = Bill.query.get(project, bill_id)
        if not bill:
            return 404, "Not Found"
        return bill

    def list(self, project):
        return project.get_bills().all()

    def add(self, project):
        form = BillForm(csrf_enabled=False)
        if form.validate():
            bill = Bill()
            form.save(bill)
            db.session.add(bill)
            db.session.commit()
            return 200, bill.id
        return 400, form.errors

    def update(self, project, bill_id):
        form = BillForm(csrf_enabled=False)
        if form.validate():
            form.save(bill)
            db.session.commit()
            return 200, bill.id
        return 400, form.errors

    def delete(self, project, bill_id):
        bill = Bill.query.delete(project, bill_id)
        if not bill:
            return 404, "Not Found"
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
