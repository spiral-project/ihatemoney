from collections import defaultdict

from flask import *
from flaskext.mail import Mail, Message
import werkzeug

# local modules
from models import db, Project, Person, Bill
from forms import *
from utils import Redirect303

"""
The blueprint for the web interface.

Contains all the interaction logic with the end user (except forms which
are directly handled in the forms module.

Basically, this blueprint takes care of the authentication and provides
some shortcuts to make your life better when coding (see `pull_project` 
and `add_project_id` for a quick overview
"""

main = Blueprint("main", __name__)
mail = Mail()

@main.url_defaults
def add_project_id(endpoint, values):
    """Add the project id to the url calls if it is expected.

    This is to not carry it everywhere in the templates.
    """
    if 'project_id' in values or not hasattr(g, 'project'):
        return
    if current_app.url_map.is_endpoint_expecting(endpoint, 'project_id'):
        values['project_id'] = g.project.id

@main.url_value_preprocessor
def pull_project(endpoint, values):
    """When a request contains a project_id value, transform it directly
    into a project by checking the credentials are stored in session.

    If not, redirect the user to an authentication form
    """
    if endpoint == "authenticate":
        return
    if not values:
        values = {}
    project_id = values.pop('project_id', None)
    if project_id:
        project = Project.query.get(project_id)
        if not project:
            raise Redirect303(url_for(".create_project", project_id=project_id))
        if project.id in session and session[project.id] == project.password:
            # add project into kwargs and call the original function
            g.project = project
        else:
            # redirect to authentication page
            raise Redirect303(
                    url_for(".authenticate", project_id=project_id))

@main.route("/authenticate", methods=["GET", "POST"])
def authenticate(project_id=None):
    """Authentication form"""
    form = AuthenticationForm()
    if not form.id.data and request.args.get('project_id'):
        form.id.data = request.args['project_id']
    project_id = form.id.data 
    project = Project.query.get(project_id)
    create_project = False # We don't want to create the project by default
    if not project:
        # But if the user try to connect to an unexisting project, we will 
        # propose him a link to the creation form.
        if request.method == "POST":
            form.validate()
        else:
            create_project = project_id

    else:
        # if credentials are already in session, redirect
        if project_id in session and project.password == session[project_id]:
            setattr(g, 'project', project)
            return redirect(url_for(".list_bills"))

        # else process the form
        if request.method == "POST":
            if form.validate():
                if not form.password.data == project.password:
                    form.errors['password'] = ["This private code is not the right one"]
                else:
                    # maintain a list of visited projects
                    if "projects" not in session:
                        session["projects"] = []
                    # add the project on the top of the list
                    session["projects"].insert(0, (project_id, project.name))
                    session[project_id] = form.password.data
                    session.update()
                    setattr(g, 'project', project)
                    return redirect(url_for(".list_bills"))

    return render_template("authenticate.html", form=form, 
            create_project=create_project)

@main.route("/")
def home():
    project_form = ProjectForm()
    auth_form = AuthenticationForm()
    return render_template("home.html", project_form=project_form, 
            auth_form=auth_form, session=session)

@main.route("/create", methods=["GET", "POST"])
def create_project():
    form = ProjectForm()
    if request.method == "GET" and 'project_id' in request.values:
        form.name.data = request.values['project_id']

    if request.method == "POST":
        # At first, we don't want the user to bother with the identifier
        # so it will automatically be missing because not displayed into the form
        # Thus we fill it with the same value as the filled name, the validation will
        # take care of the slug
        if not form.id.data:
            form.id.data = form.name.data
        if form.validate():
            # save the object in the db
            project = form.save()
            db.session.add(project)
            db.session.commit()

            # create the session object (authenticate)
            session[project.id] = project.password
            session.update()

            # send reminder email
            g.project = project
            
            message_title = "You have just created '%s' to share your expenses" % g.project.name

            message_body = render_template("reminder_mail")

            msg = Message(message_title, 
                body=message_body, 
                recipients=[project.contact_email])
            mail.send(msg)

            # redirect the user to the next step (invite)
            flash("The project identifier is %s" % project.id)
            return redirect(url_for(".invite", project_id=project.id))

    return render_template("create_project.html", form=form)

@main.route("/password-reminder", methods=["GET", "POST"])
def remind_password():
    form = PasswordReminder()
    if request.method == "POST":
        if form.validate():
            # get the project
            project = Project.query.get(form.id.data)

            # send the password reminder
            mail.send(Message("password recovery", 
                body=render_template("password_reminder", project=project), 
                recipients=[project.contact_email]))
            flash("a mail has been sent to you with the password")

    return render_template("password_reminder.html", form=form)


@main.route("/<project_id>/edit", methods=["GET", "POST"])
def edit_project():
    form = EditProjectForm()
    if request.method == "POST":
        if form.validate():
            project = form.update(g.project)
            db.session.commit()
            session[project.id] = project.password

            return redirect(url_for(".list_bills"))
    else:
        form.name.data = g.project.name
        form.password.data = g.project.password
        form.contact_email.data = g.project.contact_email

    return render_template("edit_project.html", form=form)


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

    Create a demo project if it doesnt exists yet (or has been deleted)
    """
    project = Project.query.get("demo")
    if not project:
        project = Project(id="demo", name=u"demonstration", password="demo", 
                contact_email="demo@notmyidea.org")
        db.session.add(project)
        db.session.commit()
    session[project.id] = project.password
    return redirect(url_for(".list_bills", project_id=project.id))

@main.route("/<project_id>/invite", methods=["GET", "POST"])
def invite():
    """Send invitations for this particular project"""

    form = InviteForm()

    if request.method == "POST": 
        if form.validate():
            # send the email

            message_body = render_template("invitation_mail")

            message_title = "You have been invited to share your"\
                    + " expenses for %s" % g.project.name
            msg = Message(message_title, 
                body=message_body, 
                recipients=[email.strip() 
                    for email in form.emails.data.split(",")])
            mail.send(msg)
            flash("You invitations have been sent")
            return redirect(url_for(".list_bills"))

    return render_template("send_invites.html", form=form)

@main.route("/<project_id>/")
def list_bills():
    bills = g.project.get_bills()
    return render_template("list_bills.html", 
            bills=bills, member_form=MemberForm(g.project),
            bill_form=get_billform_for(g.project)
    )

@main.route("/<project_id>/members/add", methods=["GET", "POST"])
def add_member():
    # FIXME manage form errors on the list_bills page
    form = MemberForm(g.project)
    if request.method == "POST":
        if form.validate():
            member = form.save(g.project, Person())
            db.session.commit()
            flash("%s is had been added" % member.name)
            return redirect(url_for(".list_bills"))

    return render_template("add_member.html", form=form)

@main.route("/<project_id>/members/<member_id>/reactivate", methods=["GET",])
def reactivate(member_id):
    person = Person.query.filter(Person.id == member_id)\
                .filter(Project.id == g.project.id).all()
    if person:
        person[0].activated = True
        db.session.commit()
        flash("%s is part of this project again" % person[0].name)
    return redirect(url_for(".list_bills"))


@main.route("/<project_id>/members/<member_id>/delete", methods=["GET", "POST"])
def remove_member(member_id):
    member = g.project.remove_member(member_id)
    if member.activated == False:
        flash("User '%s' has been desactivated" % member.name)
    else:
        flash("User '%s' has been removed" % member.name)

    return redirect(url_for(".list_bills"))

@main.route("/<project_id>/add", methods=["GET", "POST"])
def add_bill():
    form = get_billform_for(g.project)
    if request.method == 'POST':
        if form.validate():
            bill = Bill()
            db.session.add(form.save(bill, g.project))
            db.session.commit()

            flash("The bill has been added")
            return redirect(url_for('.list_bills'))

    return render_template("add_bill.html", form=form)


@main.route("/<project_id>/delete/<int:bill_id>")
def delete_bill(bill_id):
    # fixme: everyone is able to delete a bill
    bill = Bill.query.get(g.project, bill_id)
    if not bill:
        raise werkzeug.exceptions.NotFound()

    db.session.delete(bill)
    db.session.commit()
    flash("The bill has been deleted")

    return redirect(url_for('.list_bills'))


@main.route("/<project_id>/edit/<int:bill_id>", methods=["GET", "POST"])
def edit_bill(bill_id):
    # FIXME: Test this bill belongs to this project !
    bill = Bill.query.get(g.project, bill_id)
    if not bill:
        raise werkzeug.exceptions.NotFound()

    form = get_billform_for(g.project, set_default=False)

    if request.method == 'POST' and form.validate():
        form.save(bill, g.project)
        db.session.commit()

        flash("The bill has been modified")
        return redirect(url_for('.list_bills'))

    form.fill(bill)
    return render_template("add_bill.html", form=form, edit=True)

@main.route("/<project_id>/compute")
def compute_bills():
    """Compute the sum each one have to pay to each other and display it"""
    return render_template("compute_bills.html")

@main.route("/<project_id>/archives/create")
def create_archive():
    form = CreateArchiveForm() 
    if request.method == "POST":
        if form.validate():
            pass
            flash("The data from XX to XX has been archived")

    return render_template("create_archive.html", form=form)
