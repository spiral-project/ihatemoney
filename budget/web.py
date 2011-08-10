from collections import defaultdict

from flask import (Flask, session, request, redirect, url_for, render_template, 
        flash)
from flaskext.mail import Mail, Message

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


@app.route("/")
def home():
    project_form = ProjectForm()
    auth_form = AuthenticationForm()
    return render_template("home.html", project_form=project_form, 
            auth_form=auth_form, session=session)

@app.route("/authenticate", methods=["GET", "POST"])
def authenticate(redirect_url=None):
    form = AuthenticationForm()
    
    project_id = form.id.data

    redirect_url = redirect_url or url_for("list_bills", project_id=project_id)
    project = Project.query.get(project_id)
    create_project = False # We don't want to create the project by default
    if not project:
        # But if the user try to connect to an unexisting project, we will 
        # propose him a link to the creation form.
        create_project = project_id

    else:
        # if credentials are already in session, redirect
        if project_id in session and project.password == session[project_id]:
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
                    return redirect(redirect_url)

    return render_template("authenticate.html", form=form, 
            create_project=create_project)

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

@app.route("/<string:project_id>/invite", methods=["GET", "POST"])
@requires_auth
def invite(project):

    form = InviteForm()

    if request.method == "POST": 
        if form.validate():
            # send the email

            message_body = render_template("invitation_mail", 
                    email=project.contact_email, project=project)

            message_title = "You have been invited to share your"\
                    + " expenses for %s" % project.name
            msg = Message(message_title, 
                body=message_body, 
                recipients=[email.strip() 
                    for email in form.emails.data.split(",")])
            mail.send(msg)
            return redirect(url_for("list_bills", project_id=project.id))

    return render_template("send_invites.html", form=form, project=project)

@app.route("/<string:project_id>/")
@requires_auth
def list_bills(project):
    bills = Bill.query.join(Person, Project)\
        .filter(Bill.payer_id == Person.id)\
        .filter(Person.project_id == Project.id)\
        .filter(Project.id == project.id)\
        .order_by(Bill.date.desc())
    return render_template("list_bills.html", 
            bills=bills, project=project, 
            member_form=MemberForm(project),
            bill_form=get_billform_for(project)
    )

@app.route("/<string:project_id>/members/add", methods=["GET", "POST"])
@requires_auth
def add_member(project):
    # FIXME manage form errors on the list_bills page
    form = MemberForm(project)
    if request.method == "POST":
        if form.validate():
            db.session.add(Person(name=form.name.data, project=project))
            db.session.commit()
            return redirect(url_for("list_bills", project_id=project.id))
    return render_template("add_member.html", form=form, project=project)

@app.route("/<string:project_id>/members/<int:member_id>/delete", methods=["GET", "POST"])
@requires_auth
def remove_member(project, member_id):
    person = Person.query.get_or_404(member_id)
    if person.project == project:
        if not person.is_used():
            db.session.delete(person)
            db.session.commit()
            flash("User '%s' has been removed" % person.name)
        else:
            person.activated = False
            db.session.commit()
            flash("User '%s' has been desactivated" % person.name)
    return redirect(url_for("list_bills", project_id=project.id))

@app.route("/<string:project_id>/add", methods=["GET", "POST"])
@requires_auth
def add_bill(project):
    form = get_billform_for(project)
    if request.method == 'POST':
        if form.validate():
            bill = Bill()
            db.session.add(form.save(bill))
            db.session.commit()

            flash("The bill has been added")
            return redirect(url_for('list_bills', project_id=project.id))

    form.set_default()
    return render_template("add_bill.html", form=form, project=project)


@app.route("/<string:project_id>/delete/<int:bill_id>")
@requires_auth
def delete_bill(project, bill_id):
    bill = Bill.query.get_or_404(bill_id)
    db.session.delete(bill)
    # FIXME Delete also billowers relations
    db.session.commit()
    flash("The bill has been deleted")

    return redirect(url_for('list_bills', project_id=project.id))


@app.route("/<string:project_id>/edit/<int:bill_id>", methods=["GET", "POST"])
@requires_auth
def edit_bill(project, bill_id):
    bill = Bill.query.get_or_404(bill_id)
    form = get_billform_for(project)
    if request.method == 'POST' and form.validate():
        # FIXME Edit also billowers relations
        form.save(bill)
        db.session.commit()

        flash("The bill has been modified")
        return redirect(url_for('list_bills', project_id=project.id))

    form.fill(bill)
    return render_template("edit_bill.html", form=form, project=project, bill_id=bill_id)

@app.route("/<string:project_id>/compute")
@requires_auth
def compute_bills(project):
    """Compute the sum each one have to pay to each other and display it"""
    return render_template("compute_bills.html", project=project)


@app.route("/<string:project_id>/reset")
@requires_auth
def reset_bills(project):
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
