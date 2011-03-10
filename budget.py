from datetime import datetime

from flask import *
from flaskext.wtf import (Form, SelectField, SelectMultipleField, SubmitField,
                          DateTimeField, Required, TextField)
from flaskext.wtf.html5 import DecimalField
from flaskext.sqlalchemy import SQLAlchemy

# configuration
DEBUG = True
SQLALCHEMY_DATABASE_URI = 'sqlite:///budget.db'
SQLACHEMY_ECHO = DEBUG
PAYERS = ["Raph", "Joel", "Alexis", "Nick", "Julius"]
PAYER_CHOICES = [(p.lower(), p) for p in PAYERS]
SECRET_KEY = "tralala"


# create the application, initialize stuff
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('BUDGET_SETTINGS', silent=True)

db = SQLAlchemy(app)

# define models
class Bill(db.Model):
    __tablename__ = "bills"

    id = db.Column(db.Integer, primary_key=True)
    what = db.Column(db.UnicodeText)
    payer = db.Column(db.Unicode(200))
    amount = db.Column(db.Float)
    date = db.Column(db.Date, default=datetime.now)
    processed = db.Column(db.Boolean, default=False)

    def pay_each(self):
        """Compute what each person have to pay"""
        return round(self.amount / len(self.owers), 2)

    def __repr__(self):
        return "<Bill of %s from %s for %s>" % (self.amount, 
                self.payer, ", ".join([o.name for o in self.owers]))



class BillOwer(db.Model):
    __tablename__ = "billowers"

    bill_id = db.Column(db.Integer, db.ForeignKey("bills.id"), primary_key=True)
    name = db.Column(db.Unicode(200), primary_key=True)

    bill = db.relationship(Bill, backref=db.backref('owers', order_by=name))


# define forms
class BillForm(Form):
    what = TextField("What?", validators=[Required()])
    payer = SelectField("Payer", validators=[Required()], choices=PAYER_CHOICES)
    amount = DecimalField("Amount payed", validators=[Required()])
    payed_for = SelectMultipleField("Who have to pay for this?", validators=[Required()], choices=PAYER_CHOICES)
    submit = SubmitField("Add the bill")


@app.route("/")
def list_bills():
    bills = Bill.query.filter(Bill.processed==False).order_by(Bill.id.asc())
    return render_template("list_bills.html", bills=bills)


@app.route("/add", methods=["GET", "POST"])
def add_bill():
    form = BillForm()
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
        
    return render_template("add_bill.html", form=form)


@app.route("/compute")
def compute_bills():
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

    return render_template("compute_bills.html", balances=balances)


@app.route("/reset")
def reset_bills():
    """Reset the list of bills"""
    # get all the bills which are not processed
    bills = Bill.query.filter(Bill.processed == False)
    for bill in bills:
        bill.processed = True
        db.session.commit()

    return redirect(url_for('list_bills'))



if __name__ == '__main__':
    db.create_all()
    app.run(host="0.0.0.0", debug=True)
