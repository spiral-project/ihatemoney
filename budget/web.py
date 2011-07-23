from flask import Flask, session, request, redirect, url_for, render_template

# local modules
from models import db, Project, Person, Bill
from forms import CreationForm, AuthenticationForm, BillForm
from utils import get_billform_for, requires_auth

# create the application, initialize stuff
app = Flask(__name__)

@app.route("/")
def home():
    return "this is the homepage"

@app.route("/create")
def create_project():
    form = CreationForm()
    if 'project_id' in request.values:
        form.name.data = request.values['project_id']

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


def main():
    app.config.from_object("default_settings")
    db.init_app(app)
    db.app = app
    db.create_all()

    app.run(host="0.0.0.0", debug=True)

if __name__ == '__main__':
    main()
