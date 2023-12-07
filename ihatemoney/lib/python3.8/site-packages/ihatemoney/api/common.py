from functools import wraps

from flask import current_app, request
from flask_restful import Resource, abort
from werkzeug.security import check_password_hash
from wtforms.fields import BooleanField

from ihatemoney.currency_convertor import CurrencyConverter
from ihatemoney.emails import send_creation_email
from ihatemoney.forms import EditProjectForm, MemberForm, ProjectForm, get_billform_for
from ihatemoney.models import Bill, Person, Project, db


def need_auth(f):
    """Check the request for basic authentication for a given project.

    Return the project if the authorization is good, abort the request with a 401 otherwise
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        project_id = kwargs.get("project_id").lower()

        # Use Basic Auth
        if auth and project_id and auth.username.lower() == project_id:
            project = Project.query.get(auth.username.lower())
            if project and check_password_hash(project.password, auth.password):
                # The whole project object will be passed instead of project_id
                kwargs.pop("project_id")
                return f(*args, project=project, **kwargs)
        else:
            # Use Bearer token Auth
            auth_header = request.headers.get("Authorization", "")
            auth_token = ""
            try:
                auth_token = auth_header.split(" ")[1]
            except IndexError:
                abort(401)
            project_id = Project.verify_token(
                auth_token, token_type="auth", project_id=project_id
            )
            if auth_token and project_id:
                project = Project.query.get(project_id)
                if project:
                    kwargs.pop("project_id")
                    return f(*args, project=project, **kwargs)
        abort(401)

    return wrapper


class CurrenciesHandler(Resource):
    currency_helper = CurrencyConverter()

    def get(self):
        return self.currency_helper.get_currencies()


class ProjectsHandler(Resource):
    def post(self):
        form = ProjectForm(meta={"csrf": False})
        if form.validate() and current_app.config.get("ALLOW_PUBLIC_PROJECT_CREATION"):
            project = form.save()
            db.session.add(project)
            db.session.commit()
            send_creation_email(project)
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
        form = EditProjectForm(id=project.id, meta={"csrf": False})
        if form.validate() and current_app.config.get("ALLOW_PUBLIC_PROJECT_CREATION"):
            form.update(project)
            db.session.commit()
            send_creation_email(project)
            return "UPDATED"
        return form.errors, 400


class ProjectStatsHandler(Resource):
    method_decorators = [need_auth]

    def get(self, project):
        return project.members_stats


class APIMemberForm(MemberForm):
    """Member is not disablable via a Form.

    But we want Member.enabled to be togglable via the API.
    """

    activated = BooleanField(false_values=("false", "", "False"))

    def save(self, project, person):
        person.activated = self.activated.data
        return super(APIMemberForm, self).save(project, person)


class MembersHandler(Resource):
    method_decorators = [need_auth]

    def get(self, project):
        return project.members

    def post(self, project):
        form = MemberForm(project, meta={"csrf": False})
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
        form = APIMemberForm(project, meta={"csrf": False}, edit=True)
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
        form = get_billform_for(project, True, meta={"csrf": False})
        if form.validate():
            bill = form.export(project)
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
        form = get_billform_for(project, True, meta={"csrf": False})
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


class TokenHandler(Resource):
    method_decorators = [need_auth]

    def get(self, project):
        if not project:
            return "Not Found", 404

        token = project.generate_token()
        return {"token": token}, 200
