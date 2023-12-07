from collections import defaultdict
import datetime
import itertools

from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from debts import settle
from flask import current_app, g
from flask_sqlalchemy import BaseQuery, SQLAlchemy
from itsdangerous import (
    BadSignature,
    SignatureExpired,
    URLSafeSerializer,
    URLSafeTimedSerializer,
)
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.sql import func
from sqlalchemy_continuum import make_versioned, version_class
from sqlalchemy_continuum.plugins import FlaskPlugin

from ihatemoney.currency_convertor import CurrencyConverter
from ihatemoney.monkeypath_continuum import PatchedTransactionFactory
from ihatemoney.utils import generate_password_hash, get_members, same_bill
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
        # MonkeyPatching
        transaction_cls=PatchedTransactionFactory(),
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
    def full_balance(self):
        """Returns a triple of dicts:

        - dict mapping each member to its balance

        - dict mapping each member to how much he/she should pay others
          (i.e. how much he/she benefited from bills)

        - dict mapping each member to how much he/she should be paid by
          others (i.e. how much he/she has paid for bills)

        """
        balances, should_pay, should_receive = (defaultdict(int) for time in (1, 2, 3))

        for bill in self.get_bills_unordered().all():
            should_receive[bill.payer.id] += bill.converted_amount
            total_weight = sum(ower.weight for ower in bill.owers)
            for ower in bill.owers:
                should_pay[ower.id] += (
                    ower.weight * bill.converted_amount / total_weight
                )

        for person in self.members:
            balance = should_receive[person.id] - should_pay[person.id]
            balances[person.id] = balance

        return balances, should_pay, should_receive

    @property
    def balance(self):
        return self.full_balance[0]

    @property
    def members_stats(self):
        """Compute what each participant has paid

        :return: one stat dict per participant
        :rtype list:
        """
        balance, spent, paid = self.full_balance
        return [
            {
                "member": member,
                "paid": paid[member.id],
                "spent": spent[member.id],
                "balance": balance[member.id],
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
        for bill in self.get_bills_unordered().all():
            monthly[bill.date.year][bill.date.month] += bill.converted_amount
        return monthly

    @property
    def uses_weights(self):
        return len([i for i in self.members if i.weight != 1]) > 0

    def get_transactions_to_settle_bill(self, pretty_output=False):
        """Return a list of transactions that could be made to settle the bill"""

        def prettify(transactions, pretty_output):
            """Return pretty transactions"""
            if not pretty_output:
                return transactions
            pretty_transactions = []
            for transaction in transactions:
                pretty_transactions.append(
                    {
                        "ower": transaction["ower"].name,
                        "receiver": transaction["receiver"].name,
                        "amount": round(transaction["amount"], 2),
                        "currency": transaction["currency"],
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
                "currency": self.default_currency,
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
        return self.get_bills_unordered().count() > 0

    def has_multiple_currencies(self):
        """Returns True if multiple currencies are used"""
        # It would be more efficient to do the counting in the database,
        # but this is called very rarely so we can tolerate if it's a bit
        # slow. And doing this in Python is much more readable, see #784.
        nb_currencies = len(
            set(bill.original_currency for bill in self.get_bills_unordered())
        )
        return nb_currencies > 1

    def get_bills_unordered(self):
        """Base query for bill list"""
        # The subqueryload option allows to pre-load data from the
        # billowers table, which makes access to this data much faster.
        # Without this option, any access to bill.owers would trigger a
        # new SQL query, ruining overall performance.
        return (
            Bill.query.options(orm.subqueryload(Bill.owers))
            .join(Person, Project)
            .filter(Bill.payer_id == Person.id)
            .filter(Person.project_id == Project.id)
            .filter(Project.id == self.id)
        )

    def get_bills(self):
        """Return the list of bills related to this project"""
        return self.order_bills(self.get_bills_unordered())

    @staticmethod
    def order_bills(query):
        return (
            query.order_by(Bill.date.desc())
            .order_by(Bill.creation_date.desc())
            .order_by(Bill.id.desc())
        )

    def get_bill_weights(self):
        """
        Return all bills for this project, along with the sum of weight for each bill.
        Each line is a (float, Bill) tuple.

        Result is unordered.
        """
        return (
            db.session.query(func.sum(Person.weight), Bill)
            .options(orm.subqueryload(Bill.owers))
            .select_from(Person)
            .join(billowers, Bill, Project)
            .filter(Person.project_id == Project.id)
            .filter(Project.id == self.id)
            .group_by(Bill.id)
        )

    def get_bill_weights_ordered(self):
        """Ordered version of get_bill_weights"""
        return self.order_bills(self.get_bill_weights())

    def get_member_bills(self, member_id):
        """Return the list of bills related to a specific member"""
        return (
            self.get_bills_unordered()
            .filter(Person.id == member_id)
            .order_by(Bill.date.desc())
            .order_by(Bill.id.desc())
        )

    def get_newest_bill(self):
        """Returns the most recent bill (according to bill date) or None if there are no bills"""
        # Note that the ORM performs an optimized query with LIMIT
        return self.get_bills_unordered().order_by(Bill.date.desc()).first()

    def get_oldest_bill(self):
        """Returns the least recent bill (according to bill date) or None if there are no bills"""
        # Note that the ORM performs an optimized query with LIMIT
        return self.get_bills_unordered().order_by(Bill.date.asc()).first()

    def active_months_range(self):
        """Returns a list of dates, representing the range of consecutive months
        for which the project was active (i.e. has bills).

        Note that the list might contain months during which there was no
        bills.  We only guarantee that there were bills during the first
        and last month in the list.
        """
        oldest_bill = self.get_oldest_bill()
        newest_bill = self.get_newest_bill()
        if oldest_bill is None or newest_bill is None:
            return []
        oldest_date = oldest_bill.date
        newest_date = newest_bill.date
        newest_month = datetime.date(
            year=newest_date.year, month=newest_date.month, day=1
        )
        # Infinite iterator towards the past
        all_months = (newest_month - relativedelta(months=i) for i in itertools.count())
        # Stop when reaching one month before the first date
        months = itertools.takewhile(
            lambda x: x > oldest_date - relativedelta(months=1), all_months
        )
        return list(months)

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
                    "currency": bill.original_currency,
                    "date": str(bill.date),
                    "payer_name": Person.query.get(bill.payer_id).name,
                    "payer_weight": Person.query.get(bill.payer_id).weight,
                    "owers": owers,
                }
            )
        return pretty_bills

    def switch_currency(self, new_currency):
        if new_currency == self.default_currency:
            return
        # Update converted currency
        if new_currency == CurrencyConverter.no_currency:
            if self.has_multiple_currencies():
                raise ValueError(f"Can't unset currency of project {self.id}")

            for bill in self.get_bills_unordered():
                # We are removing the currency, and we already checked that all bills
                # had the same currency: it means that we can simply strip the currency
                # without converting the amounts. We basically ignore the current default_currency

                # Reset converted amount in case it was different from the original amount
                bill.converted_amount = bill.amount
                # Strip currency
                bill.original_currency = CurrencyConverter.no_currency
                db.session.add(bill)
        else:
            for bill in self.get_bills_unordered():
                if bill.original_currency == CurrencyConverter.no_currency:
                    # Bills that were created without currency will be set to the new currency
                    bill.original_currency = new_currency
                    bill.converted_amount = bill.amount
                else:
                    # Convert amount for others, without touching original_currency
                    bill.converted_amount = CurrencyConverter().exchange_currency(
                        bill.amount, bill.original_currency, new_currency
                    )
                db.session.add(bill)

        self.default_currency = new_currency
        db.session.add(self)
        db.session.commit()

    def import_bills(self, bills: list):
        """Import bills from a list of dictionaries"""
        # Add members not already in the project
        project_members = [str(m) for m in self.members]
        new_members = [
            m for m in get_members(bills) if str(m[0]) not in project_members
        ]
        for m in new_members:
            Person(name=m[0], project=self, weight=m[1])
        db.session.commit()

        # Import bills not already in the project
        project_bills = self.get_pretty_bills()
        id_dict = {m.name: m.id for m in self.members}
        for b in bills:
            same = False
            for p_b in project_bills:
                if same_bill(p_b, b):
                    same = True
                    break
            if not same:
                # Create bills
                try:
                    new_bill = Bill(
                        amount=b["amount"],
                        date=parse(b["date"]),
                        external_link="",
                        original_currency=b["currency"],
                        owers=Person.query.get_by_names(b["owers"], self),
                        payer_id=id_dict[b["payer_name"]],
                        project_default_currency=self.default_currency,
                        what=b["what"],
                    )
                except Exception as e:
                    raise ValueError(f"Unable to import csv data: {repr(e)}")
                db.session.add(new_bill)
        db.session.commit()

    def remove_member(self, member_id):
        """Remove a member from the project.

        If the member is not bound to a bill, then he is deleted, otherwise
        he is only deactivated.

        This method returns the status DELETED or DEACTIVATED regarding the
        changes made.
        """
        person = Person.query.get(member_id, self)
        if person is None:
            return None
        if not person.has_bills():
            db.session.delete(person)
            db.session.commit()
        else:
            person.activated = False
            db.session.commit()
        return person

    def remove_project(self):
        # We can't import at top level without circular dependencies
        from ihatemoney.history import purge_history

        db.session.delete(self)
        # Purge AFTER delete to be sure to purge the deletion from history
        purge_history(self)
        db.session.commit()

    def generate_token(self, token_type="auth"):
        """Generate a timed and serialized JsonWebToken

        :param token_type: Either "auth" for authentication (invalidated when project code changed),
                        or "reset" for password reset (invalidated after expiration),
                        or "feed" for project feeds (invalidated when project code changed)
        """

        if token_type == "reset":
            serializer = URLSafeTimedSerializer(
                current_app.config["SECRET_KEY"], salt=token_type
            )
            token = serializer.dumps([self.id])
        else:
            serializer = URLSafeSerializer(
                current_app.config["SECRET_KEY"] + self.password, salt=token_type
            )
            token = serializer.dumps([self.id])

        return token

    @staticmethod
    def verify_token(token, token_type="auth", project_id=None, max_age=3600):
        """Return the project id associated to the provided token,
        None if the provided token is expired or not valid.

        :param token: Serialized TimedJsonWebToken
        :param token_type: Either "auth" for authentication (invalidated when project code changed),
                        or "reset" for password reset (invalidated after expiration),
                        or "feed" for project feeds (invalidated when project code changed)
        :param project_id: Project ID. Used for token_type "auth" and "feed" to use the password
                        as serializer secret key.
        :param max_age: Token expiration time (in seconds). Only used with token_type "reset"
        """
        loads_kwargs = {}
        if token_type == "reset":
            serializer = URLSafeTimedSerializer(
                current_app.config["SECRET_KEY"], salt=token_type
            )
            loads_kwargs["max_age"] = max_age
        else:
            project = Project.query.get(project_id) if project_id is not None else None
            password = project.password if project is not None else ""
            serializer = URLSafeSerializer(
                current_app.config["SECRET_KEY"] + password, salt=token_type
            )
        try:
            data = serializer.loads(token, **loads_kwargs)
        except SignatureExpired:
            return None
        except BadSignature:
            return None

        data_project = data[0] if isinstance(data, list) else None
        return (
            data_project if project_id is None or data_project == project_id else None
        )

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
            default_currency="XXX",
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
        for payer, amount, owers, what in operations:
            db.session.add(
                Bill(
                    amount=amount,
                    original_currency=project.default_currency,
                    owers=[members[name] for name in owers],
                    payer_id=members[payer].id,
                    project_default_currency=project.default_currency,
                    what=what,
                )
            )

        db.session.commit()
        return project


class Person(db.Model):
    class PersonQuery(BaseQuery):
        def get_by_name(self, name, project):
            return (
                Person.query.filter(Person.name == name)
                .filter(Person.project_id == project.id)
                .one_or_none()
            )

        def get_by_names(self, names, project):
            return (
                Person.query.filter(Person.name.in_(names))
                .filter(Person.project_id == project.id)
                .all()
            )

        def get(self, id, project=None):
            if not project:
                project = g.project
            return (
                Person.query.filter(Person.id == id)
                .filter(Person.project_id == project.id)
                .one_or_none()
            )

        def get_by_ids(self, ids, project=None):
            if not project:
                project = g.project
            return (
                Person.query.filter(Person.id.in_(ids))
                .filter(Person.project_id == project.id)
                .all()
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
        """return if the participant do have bills or not"""
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
    date = db.Column(db.Date, default=datetime.datetime.now)
    creation_date = db.Column(db.Date, default=datetime.datetime.now)
    what = db.Column(db.UnicodeText)
    external_link = db.Column(db.UnicodeText)

    original_currency = db.Column(db.String(3))
    converted_amount = db.Column(db.Float)

    archive = db.Column(db.Integer, db.ForeignKey("archive.id"))

    currency_helper = CurrencyConverter()

    def __init__(
        self,
        amount: float,
        date: datetime.datetime = None,
        external_link: str = "",
        original_currency: str = "",
        owers: list = [],
        payer_id: int = None,
        project_default_currency: str = "",
        what: str = "",
    ):
        super().__init__()
        self.amount = amount
        self.date = date
        self.external_link = external_link
        self.original_currency = original_currency
        self.owers = owers
        self.payer_id = payer_id
        self.what = what
        self.converted_amount = self.currency_helper.exchange_currency(
            self.amount, self.original_currency, project_default_currency
        )

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
        """Compute what each share has to pay. Warning: this is slow, if you need
        to compute this for many bills, do it differently (see
        balance_full function)
        """
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
        """Warning: this is slow, if you need to compute this for many bills, do
        it differently (see balance_full function)
        """
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
