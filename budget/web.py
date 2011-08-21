from collections import defaultdict

from flask import *
from flaskext.mail import Mail, Message
from werkzeug.routing import RequestRedirect

# local modules
from models import db, Project, Person, Bill
from forms import ProjectForm, AuthenticationForm, BillForm, MemberForm, InviteForm
from utils import get_billform_for, requires_auth

# create the application, initialize stuff
app = Flask(__name__)
app.config.from_object("default_settings")
mail = Mail()

# db
db.init_app(app)
db.app = app
db.create_all()

# mail
mail.init_app(app)


@app.url_defaults
def add_project_id(endpoint, values):
    if 'project_id' in values or not hasattr(g, 'project'):
        return
    if app.url_map.is_endpoint_expecting(endpoint, 'project_id'):
        values['project_id'] = g.project.id

@app.url_value_preprocessor
def pull_project(endpoint, values):
    if endpoint == "authenticate":
        return
    if not values:
        values = {}
    project_id = values.pop('project_id', None)
    if project_id:
        project = Project.query.get(project_id)
        if not project:
            raise RequestRedirect(url_for("create_project", project_id=project_id))
        if project.id in session and session[project.id] == project.password:
            # add project into kwargs and call the original function
            g.project = project
        else:
            # redirect to authentication page
            raise RequestRedirect(
                    url_for("authenticate", redirect_url=request.url, 
                        project_id=project_id))

@app.route("/authenticate", methods=["GET", "POST"])
def authenticate(redirect_url=None, project_id=None):
    form = AuthenticationForm()
    project_id = form.id.data or request.args['project_id']
    project = Project.query.get(project_id)
    create_project = False # We don't want to create the project by default
    if not project:
        # But if the user try to connect to an unexisting project, we will 
        # propose him a link to the creation form.
        create_project = project_id

    else:
        # if credentials are already in session, redirect
        if project_id in session and project.password == session[project_id]:
            setattr(g, 'project', project)
            redirect_url = redirect_url or url_for("list_bills")
            return redirect(redirect_url)

        # else process the form
        if request.method == "POST":
            if form.validate():
                if not form.password.data == project.password:
                    form.errors['password'] = ["The password is not the right one"]
                else:
                    # maintain a list of visited projects
                    if "projects" not in session:
                        session["projects"] = []
                    # add the project on the top of the list
                    session["projects"].insert(0, (project_id, project.name))
                    session[project_id] = form.password.data
                    session.update()
                    setattr(g, 'project', project)
                    redirect_url = redirect_url or url_for("list_bills")
                    return redirect(redirect_url)

    return render_template("authenticate.html", form=form, 
            create_project=create_project)

@app.route("/")
def home():
    project_form = ProjectForm()
    auth_form = AuthenticationForm()
    return render_template("home.html", project_form=project_form, 
            auth_form=auth_form, session=session)

@app.route("/create", methods=["GET", "POST"])
def create_project():
    form = ProjectForm()
    if request.method == "GET" and 'project_id' in request.values:
        form.name.data = request.values['project_id']

    if request.method == "POST":
        if form.validate():
            # save the object in the db
            project = form.save()
            db.session.add(project)
            db.session.commit()

            # create the session object (authenticate)
            session[project.id] = project.password
            session.update()

            # redirect the user to the next step (invite)
            return redirect(url_for("invite", project_id=project.id))

    return render_template("create_project.html", form=form)

@app.route("/exit")
def exit():
    # delete the session
    session.clear()
    return redirect(url_for("home"))

@app.route("/demo")
def demo():
    project = Project.query.get("demo")
    if not project:
        project = Project(id="demo", name=u"demonstration", password="demo", 
                contact_email="demo@notmyidea.org")
        db.session.add(project)
        db.session.commit()
    session[project.id] = project.password
    return redirect(url_for("list_bills", project_id=project.id))

@app.route("/<project_id>/invite", methods=["GET", "POST"])
def invite():

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
            return redirect(url_for("list_bills"))

    return render_template("send_invites.html", form=form)

@app.route("/<project_id>/")
def list_bills():
    bills = Bill.query.join(Person, Project)\
        .filter(Bill.payer_id == Person.id)\
        .filter(Person.project_id == Project.id)\
        .filter(Project.id == g.project.id)\
        .order_by(Bill.date.desc())
    return render_template("list_bills.html", 
            bills=bills, member_form=MemberForm(g.project),
            bill_form=get_billform_for(g.project)
    )

@app.route("/<project_id>/members/add", methods=["GET", "POST"])
def add_member():
    # FIXME manage form errors on the list_bills page
    form = MemberForm(g.project)
    if request.method == "POST":
        if form.validate():
            db.session.add(Person(name=form.name.data, project=g.project))
            db.session.commit()
            return redirect(url_for("list_bills"))
    return render_template("add_member.html", form=form)

@app.route("/<project_id>/members/<member_id>/delete", methods=["GET", "POST"])
def remove_member(member_id):
    person = Person.query.get_or_404(member_id)
    if person.project == g.project:
        if not person.has_bills():
            db.session.delete(person)
            db.session.commit()
            flash("User '%s' has been removed" % person.name)
        else:
            person.activated = False
            db.session.commit()
            flash("User '%s' has been desactivated" % person.name)
    return redirect(url_for("list_bills"))

@app.route("/<project_id>/add", methods=["GET", "POST"])
def add_bill():
    form = get_billform_for(g.project)
    if request.method == 'POST':
        if form.validate():
            bill = Bill()
            db.session.add(form.save(bill))
            db.session.commit()

            flash("The bill has been added")
            return redirect(url_for('list_bills'))

    return render_template("add_bill.html", form=form)


@app.route("/<project_id>/delete/<int:bill_id>")
def delete_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    db.session.delete(bill)
    db.session.commit()
    flash("The bill has been deleted")

    return redirect(url_for('list_bills'))


@app.route("/<project_id>/edit/<int:bill_id>", methods=["GET", "POST"])
def edit_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    form = get_billform_for(g.project, set_default=False)
    if request.method == 'POST' and form.validate():
        form.save(bill)
        db.session.commit()

        flash("The bill has been modified")
        return redirect(url_for('list_bills'))

    form.fill(bill)
    return render_template("add_bill.html", form=form, edit=True)

@app.route("/<project_id>/compute")
def compute_bills():
    """Compute the sum each one have to pay to each other and display it"""
    return render_template("compute_bills.html")


@app.route("/<project_id>/reset")
def reset_bills():
    """Reset the list of bills"""
    # FIXME replace with the archive feature
    # get all the bills which are not processed
    bills = Bill.query.filter(Bill.processed == False)
    for bill in bills:
        bill.processed = True
        db.session.commit()

    return redirect(url_for('list_bills'))


def main():
    app.run(host="0.0.0.0", debug=True)

if __name__ == '__main__':
    main()
