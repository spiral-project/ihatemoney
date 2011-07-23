from datetime import datetime
from functools import wraps

from flask import *
from flaskext.wtf import *
from flaskext.sqlalchemy import SQLAlchemy

# configuration
DEBUG = True
SQLALCHEMY_DATABASE_URI = 'sqlite:///budget.db'
SQLACHEMY_ECHO = DEBUG
SECRET_KEY = "tralala"


# create the application, initialize stuff
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('BUDGET_SETTINGS', silent=True)

db = SQLAlchemy(app)


# define models
class Project(db.Model):
    id = db.Column(db.String, primary_key=True)

    name = db.Column(db.UnicodeText)
    password = db.Column(db.String)
    contact_email = db.Column(db.String)
    members = db.relationship("Person", backref="project")

    def __repr__(self):
        return "<Project %s>" % self.name


class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"))
    bills = db.relationship("Bill", backref="payer")

    name = db.Column(db.UnicodeText)
    status = db.Column(db.Boolean)

    def __repr__(self):
        return "<Person %s for project %s>" % (self.name, self.project.name)

# We need to manually define a join table for m2m relations
billowers = db.Table('billowers',
    db.Column('bill_id', db.Integer, db.ForeignKey('bill.id')),
    db.Column('person_id', db.Integer, db.ForeignKey('person.id')),
)

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    payer_id = db.Column(db.Integer, db.ForeignKey("person.id"))
    owers = db.relationship(Person, secondary=billowers)

    amount = db.Column(db.Float)
    date = db.Column(db.Date, default=datetime.now)
    what = db.Column(db.UnicodeText)

    def pay_each(self):
        """Compute what each person has to pay"""
        return round(self.amount / len(self.owers), 2)

    def __repr__(self):
        return "<Bill of %s from %s for %s>" % (self.amount,
                self.payer, ", ".join([o.name for o in self.owers]))


db.create_all()


# define forms
class CreationForm(Form):
    name = TextField("Project name", validators=[Required()])
    id = TextField("Project identifier", validators=[Required()])
    password = PasswordField("Password", validators=[Required()])
    contact_email = TextField("Email", validators=[Required(), Email()])
    submit = SubmitField("Get in")


class AuthenticationForm(Form):
    password = TextField("Password", validators=[Required()])
    submit = SubmitField("Get in")


class BillForm(Form):
    what = TextField("What?", validators=[Required()])
    payer = SelectField("Payer", validators=[Required()])
    amount = DecimalField("Amount payed", validators=[Required()])
    payed_for = SelectMultipleField("Who has to pay for this?", validators=[Required()])
    submit = SubmitField("Add the bill")


# utils
def get_billform_for(project_id):
    """Return an instance of BillForm configured for a particular project."""
    form = BillForm()
    payers = [(m.id, m.name) for m in Project.query.get("blah").members]
    form.payed_for.choices = form.payer.choices = payers
    return form

def requires_auth(f):
    """Decorator checking that the user do have access to the given project id.

    If not, redirects to an authentication page, otherwise display the requested
    page.
    """

    @wraps(f)
    def decorator(*args, **kwargs):
        # if a project id is specified in kwargs, check we have access to it
        # get the password matching this project id
        # pop project_id out of the kwargs
        project_id = kwargs.pop('project_id')
        project = Project.query.get(project_id)
        if not project:
            return redirect(url_for("create_project", project_id=kwargs['project_id']))

        if project.id in session and session[project.id] == project.password:
            # add project into kwargs and call the original function
            kwargs['project'] = project
            return f(*args, **kwargs)
        else:
            # redirect to authentication page
            return redirect(url_for("authenticate",
                project_id=project.id, redirect_url=request.url))
    return decorator


# views

@app.route("/")
def home():
    return "this is the homepage"

@app.route("/create")
def create_project(project_id=None):
    form = CreationForm()

    if request.method == "POST":
        if form.validate():
            # populate object & redirect
            pass

    return render_template("create_project.html", form=form)

@app.route("/<string:project_id>/")
@requires_auth
def list_bills(project):
    bills = Bill.query.order_by(Bill.id.asc())
    return render_template("list_bills.html", 
            bills=bills, project=project)


@app.route("/<string:project_id>/authenticate", methods=["GET", "POST"])
def authenticate(project_id, redirect_url=None):
    project = Project.query.get(project_id)
    redirect_url = redirect_url or url_for("list_bills", project_id=project_id)

    # if credentials are already in session, redirect
    if project_id in session and project.password == session[project_id]:
        return redirect(redirect_url)

    # else create the form and process it
    form = AuthenticationForm()
    if request.method == "POST":
        if form.validate():
            if not form.password.data == project.password:
                form.errors['password'] = ["The password is not the right one"]
            else:
                session[project_id] = form.password.data
                session.update()
                from ipdb import set_trace; set_trace()
                return redirect(redirect_url)

    return render_template("authenticate.html", form=form, project=project)


@app.route("/<string:project_id>/add", methods=["GET", "POST"])
@requires_auth
def add_bill(project):
    form = get_billform_for(project.id)
    if request.method == 'POST':
        if form.validate():
            bill = Bill()
            form.populate_obj(bill)

            for ower in form.payed_for.data:
                ower = BillOwer(name=ower)
                db.session.add(ower)
                bill.owers.append(ower)

            db.session.add(bill)


            db.session.commit()
            flash("The bill have been added")
            return redirect(url_for('list_bills'))

    return render_template("add_bill.html", form=form, project=project)


@app.route("/<string:project_id>/compute")
@requires_auth
def compute_bills(project):
    """Compute the sum each one have to pay to each other and display it"""

    balances, should_pay, should_receive = {}, {}, {}
    # for each person, get the list of should_pay other have for him
    for name, void in PAYER_CHOICES:
        bills = Bill.query.join(BillOwer).filter(Bill.processed==False)\
                .filter(BillOwer.name==name)
        for bill in bills.all():
            if name != bill.payer:
                should_pay.setdefault(name, 0)
                should_pay[name] += bill.pay_each()
                should_receive.setdefault(bill.payer, 0)
                should_receive[bill.payer] += bill.pay_each()

    for name, void in PAYER_CHOICES:
        balances[name] = should_receive.get(name, 0) - should_pay.get(name, 0)

    return render_template("compute_bills.html", balances=balances, project=project)


@app.route("/<string:project_id>/reset")
@requires_auth
def reset_bills(project):
    """Reset the list of bills"""
    # get all the bills which are not processed
    bills = Bill.query.filter(Bill.processed == False)
    for bill in bills:
        bill.processed = True
        db.session.commit()

    return redirect(url_for('list_bills'))


@app.route("/<string:project_id>/delete/<int:bill_id>")
@requires_auth
def delete_bill(project, bill_id):
    Bill.query.filter(Bill.id == bill_id).delete()
    BillOwer.query.filter(BillOwer.bill_id == bill_id).delete()
    db.session.commit()
    flash("the bill was deleted")

    return redirect(url_for('list_bills'))

@app.route("/debug/")
def debug():
    from ipdb import set_trace; set_trace()
    return render_template("debug.html")

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
