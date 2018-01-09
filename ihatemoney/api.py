# -*- coding: utf-8 -*-
from flask import Blueprint, request
from flask_restful import Resource, Api, abort
from wtforms.fields.core import BooleanField

from ihatemoney.models import db, Project, Person, Bill
from ihatemoney.forms import (ProjectForm, EditProjectForm, MemberForm,
                              get_billform_for)
from werkzeug.security import check_password_hash
from functools import wraps


api = Blueprint("api", __name__, url_prefix="/api")
restful_api = Api(api)


def need_auth(f):
    """Check the request for basic authentication for a given project.

    Return the project if the authorization is good, abort the request with a 401 otherwise
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        project_id = kwargs.get("project_id")

        if auth and project_id and auth.username == project_id:
            project = Project.query.get(auth.username)
            if project and check_password_hash(project.password, auth.password):
                # The whole project object will be passed instead of project_id
                kwargs.pop("project_id")
                return f(*args, project=project, **kwargs)
        abort(401)
    return wrapper


class ProjectsHandler(Resource):
    def post(self):
        form = ProjectForm(meta={'csrf': False})
        if form.validate():
            project = form.save()
            db.session.add(project)
            db.session.commit()
            return project.id, 201
        return form.errors, 400


class ProjectHandler(Resource):
    method_decorators = [need_auth]

    def get(self, project):
        return project

    def delete(self, project):
        db.session.delete(project)
        db.session.commit()
        return "DELETED"

    def put(self, project):
        form = EditProjectForm(meta={'csrf': False})
        if form.validate():
            form.update(project)
            db.session.commit()
            return "UPDATED"
        return form.errors, 400


class APIMemberForm(MemberForm):
    """ Member is not disablable via a Form.

    But we want Member.enabled to be togglable via the API.
    """
    activated = BooleanField(false_values=('false', '', 'False'))

    def save(self, project, person):
        person.activated = self.activated.data
        return super(APIMemberForm, self).save(project, person)


class MembersHandler(Resource):
    method_decorators = [need_auth]

    def get(self, project):
        return project.members

    def post(self, project):
        form = MemberForm(project, meta={'csrf': False})
        if form.validate():
            member = Person()
            form.save(project, member)
            db.session.commit()
            return member.id, 201
        return form.errors, 400


class MemberHandler(Resource):
    method_decorators = [need_auth]

    def get(self, project, member_id):
        member = Person.query.get(member_id, project)
        if not member or member.project != project:
            return "Not Found", 404
        return member

    def put(self, project, member_id):
        form = APIMemberForm(project, meta={'csrf': False}, edit=True)
        if form.validate():
            member = Person.query.get(member_id, project)
            form.save(project, member)
            db.session.commit()
            return member
        return form.errors, 400

    def delete(self, project, member_id):
        if project.remove_member(member_id):
            return "OK"
        return "Not Found", 404


class BillsHandler(Resource):
    method_decorators = [need_auth]

    def get(self, project):
        return project.get_bills().all()

    def post(self, project):
        form = get_billform_for(project, True, meta={'csrf': False})
        if form.validate():
            bill = Bill()
            form.save(bill, project)
            db.session.add(bill)
            db.session.commit()
            return bill.id, 201
        return form.errors, 400


class BillHandler(Resource):
    method_decorators = [need_auth]

    def get(self, project, bill_id):
        bill = Bill.query.get(project, bill_id)
        if not bill:
            return "Not Found", 404
        return bill, 200

    def put(self, project, bill_id):
        form = get_billform_for(project, True, meta={'csrf': False})
        if form.validate():
            bill = Bill.query.get(project, bill_id)
            form.save(bill, project)
            db.session.commit()
            return bill.id, 200
        return form.errors, 400

    def delete(self, project, bill_id):
        bill = Bill.query.delete(project, bill_id)
        db.session.commit()
        if not bill:
            return "Not Found", 404
        return "OK", 200


restful_api.add_resource(ProjectsHandler, '/projects')
restful_api.add_resource(ProjectHandler, '/projects/<string:project_id>')
restful_api.add_resource(MembersHandler, "/projects/<string:project_id>/members")
restful_api.add_resource(MemberHandler, "/projects/<string:project_id>/members/<int:member_id>")
restful_api.add_resource(BillsHandler, "/projects/<string:project_id>/bills")
restful_api.add_resource(BillHandler, "/projects/<string:project_id>/bills/<int:bill_id>")
