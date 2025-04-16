from functools import wraps

from flask import current_app, request
from flask_limiter.util import get_remote_address
from flask_limiter import Limiter
from flask_restful import Resource, abort
from werkzeug.security import check_password_hash
from hmac import compare_digest
from wtforms.fields import BooleanField

from ihatemoney.currency_convertor import CurrencyConverter
from ihatemoney.emails import send_creation_email
from ihatemoney.forms import EditProjectForm, MemberForm, ProjectForm, get_billform_for
from ihatemoney.models import Bill, Person, Project, db


limiter = Limiter(key_func=get_remote_address)



# Request limiter configuration
# Limiter to prevent abuse of the API
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[
    "100 per day",
    "5 per minute"
    ],
    storge_uri="redis://localhost:6379"
    storage_options={"socket_connection_timeout": 30},
    strategy="fixed-window-elastic-expiry"
)


def need_auth(f):
    @limiter.limit("5 per minute", key_func=lambda: request.authorization.username if request.authorization else get_remote_address())
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            project_id = kwargs.get("project_id", "").lower()
            if not project_id:
                abort(400, message="Invalid request")
            
            # Bearer token auth
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1].strip()  # More secure split
                if not token or len(token) > 512:  # Prevent token-based DoS
                    abort(401, message="Invalid token")
                
                verified_project_id = Project.verify_token(
                    token, 
                    token_type="auth", 
                    project_id=project_id,
                    max_age=current_app.config.get('TOKEN_EXPIRY', 86400)
                )
                if verified_project_id:
                    project = Project.query.get(verified_project_id)
                    if project:
                        kwargs.pop("project_id")
                        return f(*args, project=project, **kwargs)

            # Basic auth with constant-time comparisons
            auth = request.authorization
            if auth and project_id:
                if not compare_digest(auth.username.lower(), project_id):
                    current_app.logger.warning(f"Invalid username attempt for project {project_id}")
                    abort(401, message="Authentication failed")
                    
                project = Project.query.get(auth.username.lower())
                dummy_hash = "pbkdf2:sha256:260000$dummyhashdummyhash"
                password_hash = project.password if project else dummy_hash
                
                if project and check_password_hash(password_hash, auth.password):
                    kwargs.pop("project_id")
                    return f(*args, project=project, **kwargs)

            abort(401, message="Authentication required")
            
        except Exception as e:
            current_app.logger.error(
                f"Authentication error: {type(e).__name__}",
                extra={
                    "ip": get_remote_address(),
                    "project_id": project_id,
                    "error": str(e)
                }
            )
            abort(401, message="Authentication failed")
            
    return wrapper


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
