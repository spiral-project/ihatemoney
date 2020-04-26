"""
The blueprint for the web interface.

Contains all the interaction logic with the end user (except forms which
are directly handled in the forms module.

Basically, this blueprint takes care of the authentication and provides
some shortcuts to make your life better when coding (see `pull_project`
and `add_project_id` for a quick overview)
"""
from datetime import datetime
from functools import wraps
import json
import os
from smtplib import SMTPRecipientsRefused

from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from flask_babel import gettext as _
from flask_mail import Message
from sqlalchemy import orm
from sqlalchemy_continuum import Operation
from werkzeug.exceptions import NotFound
from werkzeug.security import check_password_hash, generate_password_hash

from ihatemoney.forms import (
    AdminAuthenticationForm,
    AuthenticationForm,
    EditProjectForm,
    InviteForm,
    MemberForm,
    PasswordReminder,
    ProjectForm,
    ResetPasswordForm,
    UploadForm,
    get_billform_for,
)
from ihatemoney.history import get_history, get_history_queries
from ihatemoney.models import Bill, LoggingMode, Person, Project, db
from ihatemoney.utils import (
    LoginThrottler,
    Redirect303,
    get_members,
    list_of_dicts2csv,
    list_of_dicts2json,
    render_localized_template,
    same_bill,
)

main = Blueprint("main", __name__)

login_throttler = LoginThrottler(max_attempts=3, delay=1)


def requires_admin(bypass=None):
    """Require admin permissions for @requires_admin decorated endpoints.

    This has no effect if ADMIN_PASSWORD is empty.

    :param bypass: Used to conditionnaly bypass the admin authentication.
                   It expects a tuple containing the name of an application
                   setting and its expected value.
                   e.g. if you use @require_admin(bypass=("ALLOW_PUBLIC_PROJECT_CREATION", True))
                   Admin authentication will be bypassed when ALLOW_PUBLIC_PROJECT_CREATION is
                   set to True.
    """

    def check_admin(f):
        @wraps(f)
        def admin_auth(*args, **kws):
            is_admin_auth_bypassed = False
            if bypass is not None and current_app.config.get(bypass[0]) == bypass[1]:
                is_admin_auth_bypassed = True
            is_admin = session.get("is_admin")
            if is_admin or is_admin_auth_bypassed:
                return f(*args, **kws)
            raise Redirect303(url_for(".admin", goto=request.path))

        return admin_auth

    return check_admin


@main.url_defaults
def add_project_id(endpoint, values):
    """Add the project id to the url calls if it is expected.

    This is to not carry it everywhere in the templates.
    """
    if "project_id" in values or not hasattr(g, "project"):
        return
    if current_app.url_map.is_endpoint_expecting(endpoint, "project_id"):
        values["project_id"] = g.project.id


@main.url_value_preprocessor
def set_show_admin_dashboard_link(endpoint, values):
    """Sets the "show_admin_dashboard_link" variable application wide
    in order to use it in the layout template.
    """

    g.show_admin_dashboard_link = (
        current_app.config["ACTIVATE_ADMIN_DASHBOARD"]
        and current_app.config["ADMIN_PASSWORD"]
    )


@main.url_value_preprocessor
def pull_project(endpoint, values):
    """When a request contains a project_id value, transform it directly
    into a project by checking the credentials stored in the session.

    With administration credentials, one can access any project.

    If not, redirect the user to an authentication form
    """
    if endpoint == "authenticate":
        return
    if not values:
        values = {}
    project_id = values.pop("project_id", None)
    if project_id:
        project = Project.query.get(project_id)
        if not project:
            raise Redirect303(url_for(".create_project", project_id=project_id))

        is_admin = session.get("is_admin")
        if session.get(project.id) or is_admin:
            # add project into kwargs and call the original function
            g.project = project
        else:
            # redirect to authentication page
            raise Redirect303(url_for(".authenticate", project_id=project_id))


@main.route("/admin", methods=["GET", "POST"])
def admin():
    """Admin authentication.

    When ADMIN_PASSWORD is empty, admin authentication is deactivated.
    """
    form = AdminAuthenticationForm()
    goto = request.args.get("goto", url_for(".home"))
    is_admin_auth_enabled = bool(current_app.config["ADMIN_PASSWORD"])
    if request.method == "POST":
        client_ip = request.remote_addr
        if not login_throttler.is_login_allowed(client_ip):
            msg = _("Too many failed login attempts, please retry later.")
            form.errors["admin_password"] = [msg]
            return render_template(
                "admin.html",
                form=form,
                admin_auth=True,
                is_admin_auth_enabled=is_admin_auth_enabled,
            )
        if form.validate():
            # Valid password
            if check_password_hash(
                current_app.config["ADMIN_PASSWORD"], form.admin_password.data
            ):
                session["is_admin"] = True
                session.update()
                login_throttler.reset(client_ip)
                return redirect(goto)
            # Invalid password
            login_throttler.increment_attempts_counter(client_ip)
            msg = _(
                "This admin password is not the right one. Only %(num)d attempts left.",
                num=login_throttler.get_remaining_attempts(client_ip),
            )
            form.errors["admin_password"] = [msg]
    return render_template(
        "admin.html",
        form=form,
        admin_auth=True,
        is_admin_auth_enabled=is_admin_auth_enabled,
    )


@main.route("/authenticate", methods=["GET", "POST"])
def authenticate(project_id=None):
    """Authentication form"""
    form = AuthenticationForm()
    # Try to get project_id from token first
    token = request.args.get("token")
    if token:
        project_id = Project.verify_token(token, token_type="non_timed_token")
        token_auth = True
    else:
        if not form.id.data and request.args.get("project_id"):
            form.id.data = request.args["project_id"]
        project_id = form.id.data
        token_auth = False
    if project_id is None:
        # User doesn't provide project identifier or a valid token
        # return to authenticate form
        msg = _("You either provided a bad token or no project identifier.")
        form.errors["id"] = [msg]
        return render_template("authenticate.html", form=form)

    project = Project.query.get(project_id)
    if not project:
        # If the user try to connect to an unexisting project, we will
        # propose him a link to the creation form.
        return render_template(
            "authenticate.html", form=form, create_project=project_id
        )

    # if credentials are already in session, redirect
    if session.get(project_id):
        setattr(g, "project", project)
        return redirect(url_for(".list_bills"))

    # else do form authentication or token authentication
    is_post_auth = request.method == "POST" and form.validate()
    if (
        is_post_auth
        and check_password_hash(project.password, form.password.data)
        or token_auth
    ):
        # maintain a list of visited projects
        if "projects" not in session:
            session["projects"] = []
        # add the project on the top of the list
        session["projects"].insert(0, (project_id, project.name))
        session[project_id] = True
        # Set session to permanent to make language choice persist
        session.permanent = True
        session.update()
        setattr(g, "project", project)
        return redirect(url_for(".list_bills"))
    if is_post_auth and not check_password_hash(project.password, form.password.data):
        msg = _("This private code is not the right one")
        form.errors["password"] = [msg]

    return render_template("authenticate.html", form=form)


@main.route("/", strict_slashes=False)
def home():
    project_form = ProjectForm()
    auth_form = AuthenticationForm()
    is_demo_project_activated = current_app.config["ACTIVATE_DEMO_PROJECT"]
    is_public_project_creation_allowed = current_app.config[
        "ALLOW_PUBLIC_PROJECT_CREATION"
    ]

    return render_template(
        "home.html",
        project_form=project_form,
        is_demo_project_activated=is_demo_project_activated,
        is_public_project_creation_allowed=is_public_project_creation_allowed,
        auth_form=auth_form,
        session=session,
    )


@main.route("/create", methods=["GET", "POST"])
@requires_admin(bypass=("ALLOW_PUBLIC_PROJECT_CREATION", True))
def create_project():
    form = ProjectForm()
    if request.method == "GET" and "project_id" in request.values:
        form.name.data = request.values["project_id"]

    if request.method == "POST":
        # At first, we don't want the user to bother with the identifier
        # so it will automatically be missing because not displayed into
        # the form
        # Thus we fill it with the same value as the filled name,
        # the validation will take care of the slug
        if not form.id.data:
            form.id.data = form.name.data
        if form.validate():
            # save the object in the db
            project = form.save()
            db.session.add(project)
            db.session.commit()

            # create the session object (authenticate)
            session[project.id] = True
            session.update()

            # send reminder email
            g.project = project

            message_title = _(
                "You have just created '%(project)s' " "to share your expenses",
                project=g.project.name,
            )

            message_body = render_localized_template("reminder_mail")

            msg = Message(
                message_title, body=message_body, recipients=[project.contact_email]
            )
            try:
                current_app.mail.send(msg)
            except SMTPRecipientsRefused:
                msg_compl = "Problem sending mail. "
                # TODO: destroy the project and cancel instead?
            else:
                msg_compl = ""

            # redirect the user to the next step (invite)
            flash(
                _(
                    "%(msg_compl)sThe project identifier is %(project)s",
                    msg_compl=msg_compl,
                    project=project.id,
                )
            )
            return redirect(url_for(".list_bills", project_id=project.id))

    return render_template("create_project.html", form=form)


@main.route("/password-reminder", methods=["GET", "POST"])
def remind_password():
    form = PasswordReminder()
    if request.method == "POST":
        if form.validate():
            # get the project
            project = Project.query.get(form.id.data)
            # send a link to reset the password
            current_app.mail.send(
                Message(
                    "password recovery",
                    body=render_localized_template(
                        "password_reminder", project=project
                    ),
                    recipients=[project.contact_email],
                )
            )
            return redirect(url_for(".password_reminder_sent"))

    return render_template("password_reminder.html", form=form)


@main.route("/password-reminder-sent", methods=["GET"])
def password_reminder_sent():
    return render_template("password_reminder_sent.html")


@main.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    form = ResetPasswordForm()
    token = request.args.get("token")
    if not token:
        return render_template(
            "reset_password.html", form=form, error=_("No token provided")
        )
    project_id = Project.verify_token(token)
    if not project_id:
        return render_template(
            "reset_password.html", form=form, error=_("Invalid token")
        )
    project = Project.query.get(project_id)
    if not project:
        return render_template(
            "reset_password.html", form=form, error=_("Unknown project")
        )

    if request.method == "POST" and form.validate():
        project.password = generate_password_hash(form.password.data)
        db.session.add(project)
        db.session.commit()
        flash(_("Password successfully reset."))
        return redirect(url_for(".home"))
    return render_template("reset_password.html", form=form)


@main.route("/<project_id>/edit", methods=["GET", "POST"])
def edit_project():
    edit_form = EditProjectForm()
    import_form = UploadForm()
    # Import form
    if import_form.validate_on_submit():
        try:
            import_project(import_form.file.data.stream, g.project)
            flash(_("Project successfully uploaded"))

            return redirect(url_for("main.list_bills"))
        except ValueError:
            flash(_("Invalid JSON"), category="error")

    # Edit form
    if edit_form.validate_on_submit():
        project = edit_form.update(g.project)
        db.session.add(project)
        db.session.commit()

        return redirect(url_for("main.list_bills"))
    else:
        edit_form.name.data = g.project.name

        if g.project.logging_preference != LoggingMode.DISABLED:
            edit_form.project_history.data = True
            if g.project.logging_preference == LoggingMode.RECORD_IP:
                edit_form.ip_recording.data = True

        edit_form.contact_email.data = g.project.contact_email

    return render_template(
        "edit_project.html",
        edit_form=edit_form,
        import_form=import_form,
        current_view="edit_project",
    )


def import_project(file, project):
    json_file = json.load(file)

    # Check if JSON is correct
    attr = ["what", "payer_name", "payer_weight", "amount", "date", "owers"]
    attr.sort()
    for e in json_file:
        if len(e) != len(attr):
            raise ValueError
        list_attr = []
        for i in e:
            list_attr.append(i)
        list_attr.sort()
        if list_attr != attr:
            raise ValueError

    # From json : export list of members
    members_json = get_members(json_file)
    members = project.members
    members_already_here = list()
    for m in members:
        members_already_here.append(str(m))

    # List all members not in the project and weight associated
    # List of tuples (name,weight)
    members_to_add = list()
    for i in members_json:
        if str(i[0]) not in members_already_here:
            members_to_add.append(i)

    # List bills not in the project
    # Same format than JSON element
    project_bills = project.get_pretty_bills()
    bill_to_add = list()
    for j in json_file:
        same = False
        for p in project_bills:
            if same_bill(p, j):
                same = True
                break
        if not same:
            bill_to_add.append(j)

    # Add users to DB
    for m in members_to_add:
        Person(name=m[0], project=project, weight=m[1])
    db.session.commit()

    id_dict = {}
    for i in project.members:
        id_dict[i.name] = i.id

    # Create bills
    for b in bill_to_add:
        owers_id = list()
        for ower in b["owers"]:
            owers_id.append(id_dict[ower])

        bill = Bill()
        form = get_billform_for(project)
        form.what = b["what"]
        form.amount = b["amount"]
        form.date = parse(b["date"])
        form.payer = id_dict[b["payer_name"]]
        form.payed_for = owers_id

        db.session.add(form.fake_form(bill, project))

    # Add bills to DB
    db.session.commit()


@main.route("/<project_id>/delete")
def delete_project():
    g.project.remove_project()
    flash(_("Project successfully deleted"))

    return redirect(request.headers.get("Referer") or url_for(".home"))


@main.route("/<project_id>/export/<string:file>.<string:format>")
def export_project(file, format):
    if file == "transactions":
        export = g.project.get_transactions_to_settle_bill(pretty_output=True)
    elif file == "bills":
        export = g.project.get_pretty_bills(export_format=format)
    else:
        abort(404, "No such export type")

    if format == "json":
        file2export = list_of_dicts2json(export)
    elif format == "csv":
        file2export = list_of_dicts2csv(export)
    else:
        abort(404, "No such export format")

    return send_file(
        file2export,
        attachment_filename=f"{g.project.id}-{file}.{format}",
        as_attachment=True,
    )


@main.route("/exit")
def exit():
    # delete the session
    session.clear()
    return redirect(url_for(".home"))


@main.route("/demo")
def demo():
    """
    Authenticate the user for the demonstration project and redirect him to
    the bills list for this project.

    Create a demo project if it doesn't exists yet (or has been deleted)
    If the demo project is deactivated, one is redirected to the create project form
    """
    is_demo_project_activated = current_app.config["ACTIVATE_DEMO_PROJECT"]
    project = Project.query.get("demo")

    if not project and not is_demo_project_activated:
        raise Redirect303(url_for(".create_project", project_id="demo"))
    if not project and is_demo_project_activated:
        project = Project(
            id="demo",
            name="demonstration",
            password=generate_password_hash("demo"),
            contact_email="demo@notmyidea.org",
        )
        db.session.add(project)
        db.session.commit()
    session[project.id] = True
    return redirect(url_for(".list_bills", project_id=project.id))


@main.route("/<project_id>/invite", methods=["GET", "POST"])
def invite():
    """Send invitations for this particular project"""

    form = InviteForm()

    if request.method == "POST":
        if form.validate():
            # send the email
            message_body = render_localized_template("invitation_mail")
            message_title = _(
                "You have been invited to share your " "expenses for %(project)s",
                project=g.project.name,
            )
            msg = Message(
                message_title,
                body=message_body,
                recipients=[email.strip() for email in form.emails.data.split(",")],
            )
            current_app.mail.send(msg)
            flash(_("Your invitations have been sent"))
            return redirect(url_for(".list_bills"))

    return render_template("send_invites.html", form=form)


@main.route("/<project_id>/")
def list_bills():
    bill_form = get_billform_for(g.project)
    # set the last selected payer as default choice if exists
    if "last_selected_payer" in session:
        bill_form.payer.data = session["last_selected_payer"]
    # Preload the "owers" relationship for all bills
    bills = (
        g.project.get_bills()
        .options(orm.subqueryload(Bill.owers))
        .paginate(per_page=100, error_out=True)
    )

    return render_template(
        "list_bills.html",
        bills=bills,
        member_form=MemberForm(g.project),
        bill_form=bill_form,
        add_bill=request.values.get("add_bill", False),
        current_view="list_bills",
    )


@main.route("/<project_id>/members/add", methods=["GET", "POST"])
def add_member():
    # FIXME manage form errors on the list_bills page
    form = MemberForm(g.project)
    if request.method == "POST":
        if form.validate():
            member = form.save(g.project, Person())
            db.session.commit()
            flash(_("%(member)s has been added", member=member.name))
            return redirect(url_for(".list_bills"))

    return render_template("add_member.html", form=form)


@main.route("/<project_id>/members/<member_id>/reactivate", methods=["POST"])
def reactivate(member_id):
    person = (
        Person.query.filter(Person.id == member_id)
        .filter(Project.id == g.project.id)
        .all()
    )
    if person:
        person[0].activated = True
        db.session.commit()
        flash(_("%(name)s is part of this project again", name=person[0].name))
    return redirect(url_for(".list_bills"))


@main.route("/<project_id>/members/<member_id>/delete", methods=["POST"])
def remove_member(member_id):
    member = g.project.remove_member(member_id)
    if member:
        if not member.activated:
            flash(
                _(
                    "User '%(name)s' has been deactivated. It will still "
                    "appear in the users list until its balance "
                    "becomes zero.",
                    name=member.name,
                )
            )
        else:
            flash(_("User '%(name)s' has been removed", name=member.name))
    return redirect(url_for(".list_bills"))


@main.route("/<project_id>/members/<member_id>/edit", methods=["POST", "GET"])
def edit_member(member_id):
    member = Person.query.get(member_id, g.project)
    if not member:
        raise NotFound()
    form = MemberForm(g.project, edit=True)

    if request.method == "POST" and form.validate():
        form.save(g.project, member)
        db.session.commit()
        flash(_("User '%(name)s' has been edited", name=member.name))
        return redirect(url_for(".list_bills"))

    form.fill(member)
    return render_template("edit_member.html", form=form, edit=True)


@main.route("/<project_id>/add", methods=["GET", "POST"])
def add_bill():
    form = get_billform_for(g.project)
    if request.method == "POST":
        if form.validate():
            # save last selected payer in session
            session["last_selected_payer"] = form.payer.data
            session.update()

            bill = Bill()
            db.session.add(form.save(bill, g.project))
            db.session.commit()

            flash(_("The bill has been added"))

            args = {}
            if form.submit2.data:
                args["add_bill"] = True

            return redirect(url_for(".list_bills", **args))

    return render_template("add_bill.html", form=form)


@main.route("/<project_id>/delete/<int:bill_id>")
def delete_bill(bill_id):
    # fixme: everyone is able to delete a bill
    bill = Bill.query.get(g.project, bill_id)
    if not bill:
        return redirect(url_for(".list_bills"))

    db.session.delete(bill)
    db.session.commit()
    flash(_("The bill has been deleted"))

    return redirect(url_for(".list_bills"))


@main.route("/<project_id>/edit/<int:bill_id>", methods=["GET", "POST"])
def edit_bill(bill_id):
    # FIXME: Test this bill belongs to this project !
    bill = Bill.query.get(g.project, bill_id)
    if not bill:
        raise NotFound()

    form = get_billform_for(g.project, set_default=False)

    if request.method == "POST" and form.validate():
        form.save(bill, g.project)
        db.session.commit()

        flash(_("The bill has been modified"))
        return redirect(url_for(".list_bills"))

    if not form.errors:
        form.fill(bill)

    return render_template("add_bill.html", form=form, edit=True)


@main.route("/lang/<lang>")
def change_lang(lang):
    session["lang"] = lang
    session.update()

    return redirect(request.headers.get("Referer") or url_for(".home"))


@main.route("/<project_id>/settle_bills")
def settle_bill():
    """Compute the sum each one have to pay to each other and display it"""
    bills = g.project.get_transactions_to_settle_bill()
    return render_template("settle_bills.html", bills=bills, current_view="settle_bill")


@main.route("/<project_id>/history")
def history():
    """Query for the version entries associated with this project."""
    history = get_history(g.project, human_readable_names=True)

    any_ip_addresses = any(event["ip"] for event in history)

    return render_template(
        "history.html",
        current_view="history",
        history=history,
        any_ip_addresses=any_ip_addresses,
        LoggingMode=LoggingMode,
        OperationType=Operation,
        current_log_pref=g.project.logging_preference,
    )


@main.route("/<project_id>/erase_history", methods=["POST"])
def erase_history():
    """Erase all history entries associated with this project."""
    for query in get_history_queries(g.project):
        query.delete(synchronize_session="fetch")

    db.session.commit()
    return redirect(url_for(".history"))


@main.route("/<project_id>/strip_ip_addresses", methods=["POST"])
def strip_ip_addresses():
    """Strip ip addresses from history entries associated with this project."""
    for query in get_history_queries(g.project):
        for version_object in query.all():
            version_object.transaction.remote_addr = None

    db.session.commit()
    return redirect(url_for(".history"))


@main.route("/<project_id>/statistics")
def statistics():
    """Compute what each member has paid and spent and display it"""
    today = datetime.now()
    return render_template(
        "statistics.html",
        members_stats=g.project.members_stats,
        monthly_stats=g.project.monthly_stats,
        months=[today - relativedelta(months=i) for i in range(12)],
        current_view="statistics",
    )


@main.route("/dashboard")
@requires_admin()
def dashboard():
    is_admin_dashboard_activated = current_app.config["ACTIVATE_ADMIN_DASHBOARD"]
    return render_template(
        "dashboard.html",
        projects=Project.query.all(),
        is_admin_dashboard_activated=is_admin_dashboard_activated,
    )


@main.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(main.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )
