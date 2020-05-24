from collections import defaultdict
from datetime import datetime

from debts import settle
from flask import current_app, g
from flask_sqlalchemy import BaseQuery, SQLAlchemy
from itsdangerous import (
    BadSignature,
    SignatureExpired,
    TimedJSONWebSignatureSerializer,
    URLSafeSerializer,
)
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.sql import func
from sqlalchemy_continuum import make_versioned, version_class
from sqlalchemy_continuum.plugins import FlaskPlugin
from werkzeug.security import generate_password_hash

from ihatemoney.patch_sqlalchemy_continuum import PatchedBuilder
from ihatemoney.versioning import (
    ConditionalVersioningManager,
    LoggingMode,
    get_ip_if_allowed,
    version_privacy_predicate,
)

make_versioned(
    user_cls=None,
    manager=ConditionalVersioningManager(
        # Conditionally Disable the versioning based on each
        # project's privacy preferences
        tracking_predicate=version_privacy_predicate,
        # Patch in a fix to a SQLAchemy-Continuum Bug.
        # See patch_sqlalchemy_continuum.py
        builder=PatchedBuilder(),
    ),
    plugins=[
        FlaskPlugin(
            # Redirect to our own function, which respects user preferences
            # on IP address collection
            remote_addr_factory=get_ip_if_allowed,
            # Suppress the plugin's attempt to grab a user id,
            # which imports the flask_login module (causing an error)
            current_user_id_factory=lambda: None,
        )
    ],
)

db = SQLAlchemy()


class Project(db.Model):
    class ProjectQuery(BaseQuery):
        def get_by_name(self, name):
            return Project.query.filter(Project.name == name).one()

    # Direct SQLAlchemy-Continuum to track changes to this model
    __versioned__ = {}

    id = db.Column(db.String(64), primary_key=True)

    name = db.Column(db.UnicodeText)
    password = db.Column(db.String(128))
    contact_email = db.Column(db.String(128))
    logging_preference = db.Column(
        db.Enum(LoggingMode),
        default=LoggingMode.default(),
        nullable=False,
        server_default=LoggingMode.default().name,
    )
    members = db.relationship("Person", backref="project")

    query_class = ProjectQuery
    default_currency = db.Column(db.String(3))

    @property
    def _to_serialize(self):
        obj = {
            "id": self.id,
            "name": self.name,
            "contact_email": self.contact_email,
            "logging_preference": self.logging_preference.value,
            "members": [],
            "default_currency": self.default_currency,
        }

        balance = self.balance
        for member in self.members:
            member_obj = member._to_serialize
            member_obj["balance"] = balance.get(member.id, 0)
            obj["members"].append(member_obj)

        return obj

    @property
    def active_members(self):
        return [m for m in self.members if m.activated]

    @property
    def balance(self):

        balances, should_pay, should_receive = (defaultdict(int) for time in (1, 2, 3))

        # for each person
        for person in self.members:
            # get the list of bills he has to pay
            bills = Bill.query.options(orm.subqueryload(Bill.owers)).filter(
                Bill.owers.contains(person)
            )
            for bill in bills.all():
                if person != bill.payer:
                    share = bill.pay_each() * person.weight
                    should_pay[person] += share
                    should_receive[bill.payer] += share

        for person in self.members:
            balance = should_receive[person] - should_pay[person]
            balances[person.id] = balance

        return balances

    @property
    def members_stats(self):
        """Compute what each member has paid

        :return: one stat dict per member
        :rtype list:
        """
        return [
            {
                "member": member,
                "paid": sum(
                    [
                        bill.converted_amount
                        for bill in self.get_member_bills(member.id).all()
                    ]
                ),
                "spent": sum(
                    [
                        bill.pay_each() * member.weight
                        for bill in self.get_bills().all()
                        if member in bill.owers
                    ]
                ),
                "balance": self.balance[member.id],
            }
            for member in self.active_members
        ]

    @property
    def monthly_stats(self):
        """Compute expenses by month

        :return: a dict of years mapping to a dict of months mapping to the amount
        :rtype dict:
        """
        monthly = defaultdict(lambda: defaultdict(float))
        for bill in self.get_bills().all():
            monthly[bill.date.year][bill.date.month] += bill.converted_amount
        return monthly

    @property
    def uses_weights(self):
        return len([i for i in self.members if i.weight != 1]) > 0

    def get_transactions_to_settle_bill(self, pretty_output=False):
        """Return a list of transactions that could be made to settle the bill"""

        def prettify(transactions, pretty_output):
            """ Return pretty transactions
            """
            if not pretty_output:
                return transactions
            pretty_transactions = []
            for transaction in transactions:
                pretty_transactions.append(
                    {
                        "ower": transaction["ower"].name,
                        "receiver": transaction["receiver"].name,
                        "amount": round(transaction["amount"], 2),
                    }
                )
            return pretty_transactions

        # cache value for better performance
        members = {person.id: person for person in self.members}
        settle_plan = settle(self.balance.items()) or []

        transactions = [
            {
                "ower": members[ower_id],
                "receiver": members[receiver_id],
                "amount": amount,
            }
            for ower_id, amount, receiver_id in settle_plan
        ]

        return prettify(transactions, pretty_output)

    def exactmatch(self, credit, debts):
        """Recursively try and find subsets of 'debts' whose sum is equal to credit"""
        if not debts:
            return None
        if debts[0]["balance"] > credit:
            return self.exactmatch(credit, debts[1:])
        elif debts[0]["balance"] == credit:
            return [debts[0]]
        else:
            match = self.exactmatch(credit - debts[0]["balance"], debts[1:])
            if match:
                match.append(debts[0])
            else:
                match = self.exactmatch(credit, debts[1:])
            return match

    def has_bills(self):
        """return if the project do have bills or not"""
        return self.get_bills().count() > 0

    def get_bills(self):
        """Return the list of bills related to this project"""
        return (
            Bill.query.join(Person, Project)
            .filter(Bill.payer_id == Person.id)
            .filter(Person.project_id == Project.id)
            .filter(Project.id == self.id)
            .order_by(Bill.date.desc())
            .order_by(Bill.creation_date.desc())
            .order_by(Bill.id.desc())
        )

    def get_member_bills(self, member_id):
        """Return the list of bills related to a specific member"""
        return (
            Bill.query.join(Person, Project)
            .filter(Bill.payer_id == Person.id)
            .filter(Person.project_id == Project.id)
            .filter(Person.id == member_id)
            .filter(Project.id == self.id)
            .order_by(Bill.date.desc())
            .order_by(Bill.id.desc())
        )

    def get_pretty_bills(self, export_format="json"):
        """Return a list of project's bills with pretty formatting"""
        bills = self.get_bills()
        pretty_bills = []
        for bill in bills:
            if export_format == "json":
                owers = [ower.name for ower in bill.owers]
            else:
                owers = ", ".join([ower.name for ower in bill.owers])

            pretty_bills.append(
                {
                    "what": bill.what,
                    "amount": round(bill.amount, 2),
                    "date": str(bill.date),
                    "payer_name": Person.query.get(bill.payer_id).name,
                    "payer_weight": Person.query.get(bill.payer_id).weight,
                    "owers": owers,
                }
            )
        return pretty_bills

    def remove_member(self, member_id):
        """Remove a member from the project.

        If the member is not bound to a bill, then he is deleted, otherwise
        he is only deactivated.

        This method returns the status DELETED or DEACTIVATED regarding the
        changes made.
        """
        try:
            person = Person.query.get(member_id, self)
        except orm.exc.NoResultFound:
            return None
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

    def generate_token(self, expiration=0):
        """Generate a timed and serialized JsonWebToken

        :param expiration: Token expiration time (in seconds)
        """
        if expiration:
            serializer = TimedJSONWebSignatureSerializer(
                current_app.config["SECRET_KEY"], expiration
            )
            token = serializer.dumps({"project_id": self.id}).decode("utf-8")
        else:
            serializer = URLSafeSerializer(current_app.config["SECRET_KEY"])
            token = serializer.dumps({"project_id": self.id})
        return token

    @staticmethod
    def verify_token(token, token_type="timed_token"):
        """Return the project id associated to the provided token,
        None if the provided token is expired or not valid.

        :param token: Serialized TimedJsonWebToken
        """
        if token_type == "timed_token":
            serializer = TimedJSONWebSignatureSerializer(
                current_app.config["SECRET_KEY"]
            )
        else:
            serializer = URLSafeSerializer(current_app.config["SECRET_KEY"])
        try:
            data = serializer.loads(token)
        except SignatureExpired:
            return None
        except BadSignature:
            return None
        return data["project_id"]

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Project {self.name}>"

    @staticmethod
    def create_demo_project():
        project = Project(
            id="demo",
            name="demonstration",
            password=generate_password_hash("demo"),
            contact_email="demo@notmyidea.org",
            default_currency="EUR",
        )
        db.session.add(project)
        db.session.commit()

        members = {}
        for name in ("Amina", "Georg", "Alice"):
            person = Person()
            person.name = name
            person.project = project
            person.weight = 1
            db.session.add(person)

            members[name] = person

        db.session.commit()

        operations = (
            ("Georg", 200, ("Amina", "Georg", "Alice"), "Food shopping"),
            ("Alice", 20, ("Amina", "Alice"), "Beer !"),
            ("Amina", 50, ("Amina", "Alice", "Georg"), "AMAP"),
        )
        for (payer, amount, owers, subject) in operations:
            bill = Bill()
            bill.payer_id = members[payer].id
            bill.what = subject
            bill.owers = [members[name] for name in owers]
            bill.amount = amount
            bill.original_currency = "EUR"
            bill.converted_amount = amount

            db.session.add(bill)

        db.session.commit()
        return project


class Person(db.Model):
    class PersonQuery(BaseQuery):
        def get_by_name(self, name, project):
            return (
                Person.query.filter(Person.name == name)
                .filter(Project.id == project.id)
                .one()
            )

        def get(self, id, project=None):
            if not project:
                project = g.project
            return (
                Person.query.filter(Person.id == id)
                .filter(Project.id == project.id)
                .one()
            )

    query_class = PersonQuery

    # Direct SQLAlchemy-Continuum to track changes to this model
    __versioned__ = {}

    __table_args__ = {"sqlite_autoincrement": True}

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(64), db.ForeignKey("project.id"))
    bills = db.relationship("Bill", backref="payer")

    name = db.Column(db.UnicodeText)
    weight = db.Column(db.Float, default=1)
    activated = db.Column(db.Boolean, default=True)

    @property
    def _to_serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "weight": self.weight,
            "activated": self.activated,
        }

    def has_bills(self):
        """return if the user do have bills or not"""
        bills_as_ower_number = (
            db.session.query(billowers)
            .filter(billowers.columns.get("person_id") == self.id)
            .count()
        )
        return bills_as_ower_number != 0 or len(self.bills) != 0

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Person {self.name} for project {self.project.name}>"


# We need to manually define a join table for m2m relations
billowers = db.Table(
    "billowers",
    db.Column("bill_id", db.Integer, db.ForeignKey("bill.id"), primary_key=True),
    db.Column("person_id", db.Integer, db.ForeignKey("person.id"), primary_key=True),
    sqlite_autoincrement=True,
)


class Bill(db.Model):
    class BillQuery(BaseQuery):
        def get(self, project, id):
            try:
                return (
                    self.join(Person, Project)
                    .filter(Bill.payer_id == Person.id)
                    .filter(Person.project_id == Project.id)
                    .filter(Project.id == project.id)
                    .filter(Bill.id == id)
                    .one()
                )
            except orm.exc.NoResultFound:
                return None

        def delete(self, project, id):
            bill = self.get(project, id)
            if bill:
                db.session.delete(bill)
            return bill

    query_class = BillQuery

    # Direct SQLAlchemy-Continuum to track changes to this model
    __versioned__ = {}

    __table_args__ = {"sqlite_autoincrement": True}

    id = db.Column(db.Integer, primary_key=True)

    payer_id = db.Column(db.Integer, db.ForeignKey("person.id"))
    owers = db.relationship(Person, secondary=billowers)

    amount = db.Column(db.Float)
    date = db.Column(db.Date, default=datetime.now)
    creation_date = db.Column(db.Date, default=datetime.now)
    what = db.Column(db.UnicodeText)
    external_link = db.Column(db.UnicodeText)

    original_currency = db.Column(db.String(3))
    converted_amount = db.Column(db.Float)

    archive = db.Column(db.Integer, db.ForeignKey("archive.id"))

    @property
    def _to_serialize(self):
        return {
            "id": self.id,
            "payer_id": self.payer_id,
            "owers": self.owers,
            "amount": self.amount,
            "date": self.date,
            "creation_date": self.creation_date,
            "what": self.what,
            "external_link": self.external_link,
            "original_currency": self.original_currency,
            "converted_amount": self.converted_amount,
        }

    def pay_each_default(self, amount):
        """Compute what each share has to pay"""
        if self.owers:
            weights = (
                db.session.query(func.sum(Person.weight))
                .join(billowers, Bill)
                .filter(Bill.id == self.id)
            ).scalar()
            return amount / weights
        else:
            return 0

    def __str__(self):
        return self.what

    def pay_each(self):
        return self.pay_each_default(self.converted_amount)

    def __repr__(self):
        return (
            f"<Bill of {self.amount} from {self.payer} for "
            f"{', '.join([o.name for o in self.owers])}>"
        )


class Archive(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(64), db.ForeignKey("project.id"))
    name = db.Column(db.UnicodeText)

    @property
    def start_date(self):
        pass

    @property
    def end_date(self):
        pass

    def __repr__(self):
        return "<Archive>"


sqlalchemy.orm.configure_mappers()

PersonVersion = version_class(Person)
ProjectVersion = version_class(Project)
BillVersion = version_class(Bill)
