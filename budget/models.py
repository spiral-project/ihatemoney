from collections import defaultdict

from datetime import datetime
from flaskext.sqlalchemy import SQLAlchemy, BaseQuery
from flask import g

from sqlalchemy import orm

db = SQLAlchemy()

# define models
class Project(db.Model):

    _to_serialize = ("id", "name", "password", "contact_email", 
            "members", "active_members", "balance")

    id = db.Column(db.String, primary_key=True)

    name = db.Column(db.UnicodeText)
    password = db.Column(db.String)
    contact_email = db.Column(db.String)
    members = db.relationship("Person", backref="project")

    @property
    def active_members(self):
        return [m for m in self.members if m.activated]

    @property
    def balance(self):

        balances, should_pay, should_receive = defaultdict(int), defaultdict(int), defaultdict(int)

        # for each person
        for person in self.members:
            # get the list of bills he has to pay
            bills = Bill.query.filter(Bill.owers.contains(person))
            for bill in bills.all():
                if person != bill.payer: 
                    should_pay[person] += bill.pay_each()
                    should_receive[bill.payer] += bill.pay_each()

        for person in self.members:
            balances[person.id] = round(should_receive[person] - should_pay[person], 2)

        return balances

    def has_bills(self):
        """return if the project do have bills or not"""
        return self.get_bills().count() != 0

    def get_bills(self):
        """Return the list of bills related to this project"""
        return Bill.query.join(Person, Project)\
            .filter(Bill.payer_id == Person.id)\
            .filter(Person.project_id == Project.id)\
            .filter(Project.id == self.id)\
            .order_by(Bill.date.desc())

    def remove_member(self, member_id):
        """Remove a member from the project.

        If the member is not bound to a bill, then he is deleted, otherwise
        he is only deactivated.

        This method returns the status DELETED or DEACTIVATED regarding the
        changes made.
        """
        person = Person.query.get(member_id, self)
        if not person.has_bills():
            db.session.delete(person)
            db.session.commit()
        else:
            person.activated = False
            db.session.commit()
        return person

    def remove_project(self):
        db.session.delete(self)
        db.session.commit()

    def __repr__(self):
        return "<Project %s>" % self.name


class Person(db.Model):

    class PersonQuery(BaseQuery):
        def get_by_name(self, name, project):
            return Person.query.filter(Person.name == name)\
                .filter(Project.id == project.id).one()

        def get(self, id, project=None):
            if not project:
                project = g.project
            return Person.query.filter(Person.id == id)\
                .filter(Project.id == project.id).one()


    query_class = PersonQuery

    _to_serialize = ("id", "name", "activated")

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String, db.ForeignKey("project.id"))
    bills = db.relationship("Bill", backref="payer")

    name = db.Column(db.UnicodeText)
    activated = db.Column(db.Boolean, default=True)

    def has_bills(self):
        """return if the user do have bills or not"""
        bills_as_ower_number = db.session.query(billowers)\
            .filter(billowers.columns.get("bill_id") == self.id)\
            .count()
        return bills_as_ower_number != 0 or len(self.bills) != 0

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<Person %s for project %s>" % (self.name, self.project.name)

# We need to manually define a join table for m2m relations
billowers = db.Table('billowers',
    db.Column('bill_id', db.Integer, db.ForeignKey('bill.id')),
    db.Column('person_id', db.Integer, db.ForeignKey('person.id')),
)

class Bill(db.Model):

    class BillQuery(BaseQuery):

        def get(self, project, id):
            try:
                return self.join(Person, Project)\
                    .filter(Bill.payer_id == Person.id)\
                    .filter(Person.project_id == Project.id)\
                    .filter(Project.id == project.id)\
                    .filter(Bill.id == id).one()
            except orm.exc.NoResultFound:
                return None

        def delete(self, project, id):
            bill = self.get(project, id)
            if bill:
                db.session.delete(bill)
            return bill

    query_class = BillQuery

    _to_serialize = ("id", "payer_id", "owers", "amount", "date", "what")

    id = db.Column(db.Integer, primary_key=True)

    payer_id = db.Column(db.Integer, db.ForeignKey("person.id"))
    owers = db.relationship(Person, secondary=billowers)

    amount = db.Column(db.Float)
    date = db.Column(db.Date, default=datetime.now)
    what = db.Column(db.UnicodeText)

    archive = db.Column(db.Integer, db.ForeignKey("archive.id"))

    def pay_each(self):
        """Compute what each person has to pay"""
        return round(self.amount / len(self.owers), 2)

    def __repr__(self):
        return "<Bill of %s from %s for %s>" % (self.amount,
                self.payer, ", ".join([o.name for o in self.owers]))

class Archive(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String, db.ForeignKey("project.id"))
    name = db.Column(db.UnicodeText)

    @property
    def start_date(self):
        pass

    @property
    def end_date(self):
        pass

    def __repr__(self):
        return "<Archive>"
