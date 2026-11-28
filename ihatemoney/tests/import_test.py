import copy
import csv
import io
import json

import pytest

from ihatemoney.models import BillType
from ihatemoney.tests.common.ihatemoney_testcase import IhatemoneyTestCase
from ihatemoney.utils import get_members, list_of_dicts2csv, list_of_dicts2json


# Data exported with Ihatemoney 6.0
# Currencies are added manually in the tests, with several cases.
# DO NOT MODIFY, this is used to check backwards compatibility.
@pytest.fixture
def import_data_6_0(request: pytest.FixtureRequest):
    data = [
        {
            "date": "2017-01-01",
            "what": "refund",
            "amount": 13.33,
            "payer_name": "tata",
            "payer_weight": 1.0,
            "owers": ["jeanne"],
        },
        {
            "date": "2016-12-31",
            "what": "red wine",
            "amount": 200.0,
            "payer_name": "jeanne",
            "payer_weight": 1.0,
            "owers": ["zorglub", "tata"],
        },
        {
            "date": "2016-12-31",
            "what": "fromage a raclette",
            "amount": 10.0,
            "payer_name": "zorglub",
            "payer_weight": 2.0,
            "owers": ["zorglub", "jeanne", "tata", "pepe"],
        },
    ]
    request.cls.data = data
    yield data


# Data exported with Ihatemoney 7.0, which added bill_type.
# Currencies are added manually in the tests, with several cases.
# DO NOT MODIFY, this is used to check backwards compatibility.
@pytest.fixture
def import_data_7_0(request: pytest.FixtureRequest):
    data = [
        {
            "date": "2017-01-01",
            "what": "refund",
            "amount": 13.33,
            "payer_name": "tata",
            "payer_weight": 1.0,
            "bill_type": "Expense",
            "owers": ["jeanne"],
        },
        {
            "date": "2016-12-31",
            "what": "red wine",
            "bill_type": "Expense",
            "amount": 200.0,
            "payer_name": "jeanne",
            "payer_weight": 1.0,
            "owers": ["zorglub", "tata"],
        },
        {
            "date": "2016-12-31",
            "bill_type": "Expense",
            "what": "fromage a raclette",
            "amount": 10.0,
            "payer_name": "zorglub",
            "payer_weight": 2.0,
            "owers": ["zorglub", "jeanne", "tata", "pepe"],
        },
    ]
    request.cls.data = data
    yield data


class CommonTestCase:

    class Import(IhatemoneyTestCase):

        def populate_data_with_currencies(self, currencies):
            for d in range(len(self.data)):
                self.data[d]["currency"] = currencies[d]

        def test_import_currencies_in_empty_project_with_currency(self):
            # Import JSON with currencies in an empty project with a default currency

            self.post_project("raclette", default_currency="EUR")
            self.login("raclette")

            project = self.get_project("raclette")

            self.populate_data_with_currencies(["EUR", "CAD", "EUR"])
            self.import_project("raclette", self.generate_form_data(self.data))

            bills = project.get_pretty_bills()

            # Check if all bills have been added
            assert len(bills) == len(self.data)

            # Check if name of bills are ok
            b = [e["what"] for e in bills]
            b.sort()
            ref = [e["what"] for e in self.data]
            ref.sort()

            assert b == ref

            # Check if other informations in bill are ok
            for d in self.data:
                for b in bills:
                    if b["what"] == d["what"]:
                        assert b["payer_name"] == d["payer_name"]
                        assert b["amount"] == d["amount"]
                        assert b["currency"] == d["currency"]
                        assert b["payer_weight"] == d["payer_weight"]
                        assert b["date"] == d["date"]
                        assert b["bill_type"] == d.get("bill_type", BillType.default_value())
                        list_project = [ower for ower in b["owers"]]
                        list_project.sort()
                        list_json = [ower for ower in d["owers"]]
                        list_json.sort()
                        assert list_project == list_json

        def test_import_single_currency_in_empty_project_without_currency(self):
            # Import JSON with a single currency in an empty project with no
            # default currency. It should work by stripping the currency from
            # bills.

            self.post_project("raclette")
            self.login("raclette")

            project = self.get_project("raclette")

            self.populate_data_with_currencies(["EUR", "EUR", "EUR"])
            self.import_project("raclette", self.generate_form_data(self.data))

            bills = project.get_pretty_bills()

            # Check if all bills have been added
            assert len(bills) == len(self.data)

            # Check if name of bills are ok
            b = [e["what"] for e in bills]
            b.sort()
            ref = [e["what"] for e in self.data]
            ref.sort()

            assert b == ref

            # Check if other informations in bill are ok
            for d in self.data:
                for b in bills:
                    if b["what"] == d["what"]:
                        assert b["payer_name"] == d["payer_name"]
                        assert b["amount"] == d["amount"]
                        # Currency should have been stripped
                        assert b["currency"] == "XXX"
                        assert b["payer_weight"] == d["payer_weight"]
                        assert b["date"] == d["date"]
                        assert b["bill_type"] == d.get("bill_type", BillType.default_value())
                        list_project = [ower for ower in b["owers"]]
                        list_project.sort()
                        list_json = [ower for ower in d["owers"]]
                        list_json.sort()
                        assert list_project == list_json

        def test_import_multiple_currencies_in_empty_project_without_currency(self):
            # Import JSON with multiple currencies in an empty project with no
            # default currency. It should fail.

            self.post_project("raclette")
            self.login("raclette")

            project = self.get_project("raclette")

            self.populate_data_with_currencies(["EUR", "CAD", "EUR"])
            # Import should fail
            self.import_project("raclette", self.generate_form_data(self.data), 400)

            bills = project.get_pretty_bills()

            # Check that there are no bills
            assert len(bills) == 0

        def test_import_no_currency_in_empty_project_with_currency(self):
            # Import JSON without currencies (from ihatemoney < 5) in an empty
            # project with a default currency.

            self.post_project("raclette", default_currency="EUR")
            self.login("raclette")

            project = self.get_project("raclette")

            self.import_project("raclette", self.generate_form_data(self.data))

            bills = project.get_pretty_bills()

            # Check if all bills have been added
            assert len(bills) == len(self.data)

            # Check if name of bills are ok
            b = [e["what"] for e in bills]
            b.sort()
            ref = [e["what"] for e in self.data]
            ref.sort()

            assert b == ref

            # Check if other informations in bill are ok
            for d in self.data:
                for b in bills:
                    if b["what"] == d["what"]:
                        assert b["payer_name"] == d["payer_name"]
                        assert b["amount"] == d["amount"]
                        # All bills are converted to default project currency
                        assert b["currency"] == "EUR"
                        assert b["payer_weight"] == d["payer_weight"]
                        assert b["date"] == d["date"]
                        assert b["bill_type"] == d.get("bill_type", BillType.default_value())
                        list_project = [ower for ower in b["owers"]]
                        list_project.sort()
                        list_json = [ower for ower in d["owers"]]
                        list_json.sort()
                        assert list_project == list_json

        def test_import_no_currency_in_empty_project_without_currency(self):
            # Import JSON without currencies (from ihatemoney < 5) in an empty
            # project with no default currency.

            self.post_project("raclette")
            self.login("raclette")

            project = self.get_project("raclette")

            self.import_project("raclette", self.generate_form_data(self.data))

            bills = project.get_pretty_bills()

            # Check if all bills have been added
            assert len(bills) == len(self.data)

            # Check if name of bills are ok
            b = [e["what"] for e in bills]
            b.sort()
            ref = [e["what"] for e in self.data]
            ref.sort()

            assert b == ref

            # Check if other informations in bill are ok
            for d in self.data:
                for b in bills:
                    if b["what"] == d["what"]:
                        assert b["payer_name"] == d["payer_name"]
                        assert b["amount"] == d["amount"]
                        assert b["currency"] == "XXX"
                        assert b["payer_weight"] == d["payer_weight"]
                        assert b["date"] == d["date"]
                        assert b["bill_type"] == d.get("bill_type", BillType.default_value())
                        list_project = [ower for ower in b["owers"]]
                        list_project.sort()
                        list_json = [ower for ower in d["owers"]]
                        list_json.sort()
                        assert list_project == list_json

        def test_import_partial_project(self):
            # Import a JSON in a project with already existing data

            self.post_project("raclette")
            self.login("raclette")

            project = self.get_project("raclette")

            self.client.post(
                "/raclette/members/add", data={"name": "zorglub", "weight": 2}
            )
            self.client.post("/raclette/members/add", data={"name": "jeanne"})
            self.client.post("/raclette/members/add", data={"name": "tata"})
            self.client.post(
                "/raclette/add",
                data={
                    "date": "2016-12-31",
                    "what": "red wine",
                    "bill_type": "Expense",
                    "payer": 2,
                    "payed_for": [1, 3],
                    "amount": "200",
                },
            )

            self.populate_data_with_currencies(["XXX", "XXX", "XXX"])

            self.import_project("raclette", self.generate_form_data(self.data))

            bills = project.get_pretty_bills()

            # Check if all bills have been added
            assert len(bills) == len(self.data)

            # Check if name of bills are ok
            b = [e["what"] for e in bills]
            b.sort()
            ref = [e["what"] for e in self.data]
            ref.sort()

            assert b == ref

            # Check if other informations in bill are ok
            for d in self.data:
                for b in bills:
                    if b["what"] == d["what"]:
                        assert b["payer_name"] == d["payer_name"]
                        assert b["amount"] == d["amount"]
                        assert b["currency"] == d["currency"]
                        assert b["payer_weight"] == d["payer_weight"]
                        assert b["date"] == d["date"]
                        assert b["bill_type"] == d.get("bill_type", BillType.default_value())
                        list_project = [ower for ower in b["owers"]]
                        list_project.sort()
                        list_json = [ower for ower in d["owers"]]
                        list_json.sort()
                        assert list_project == list_json

        def test_import_wrong_data(self):
            self.post_project("raclette")
            self.login("raclette")
            data_wrong_keys = [
                {
                    "checked": False,
                    "dimensions": {"width": 5, "height": 10},
                    "id": 1,
                    "name": "A green door",
                    "price": 12.5,
                    "tags": ["home", "green"],
                }
            ]
            data_amount_missing = [
                {
                    "date": "2017-01-01",
                    "what": "refund",
                    "bill_type": "Reimbursement",
                    "payer_name": "tata",
                    "payer_weight": 1.0,
                    "owers": ["jeanne"],
                }
            ]
            for data in [data_wrong_keys, data_amount_missing]:
                # Import should fail
                self.import_project("raclette", self.generate_form_data(data), 400)


class TestExport(IhatemoneyTestCase):
    def test_export(self):
        # Export a simple project without currencies

        self.post_project("raclette")

        # add participants
        self.client.post("/raclette/members/add", data={"name": "zorglub", "weight": 2})
        self.client.post("/raclette/members/add", data={"name": "jeanne"})
        self.client.post("/raclette/members/add", data={"name": "tata"})
        self.client.post("/raclette/members/add", data={"name": "pépé"})

        # create bills
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "bill_type": "Expense",
                "what": "à raclette",
                "payer": 1,
                "payed_for": [1, 2, 3, 4],
                "amount": "10.0",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "bill_type": "Expense",
                "what": "red wine",
                "payer": 2,
                "payed_for": [1, 3],
                "amount": "200",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2017-01-01",
                "bill_type": "Reimbursement",
                "what": "refund",
                "payer": 3,
                "payed_for": [2],
                "amount": "13.33",
            },
        )

        # generate json export of bills
        resp = self.client.get("/raclette/export/bills.json")
        expected = [
            {
                "date": "2017-01-01",
                "bill_type": "Reimbursement",
                "what": "refund",
                "amount": 13.33,
                "currency": "XXX",
                "payer_name": "tata",
                "payer_weight": 1.0,
                "owers": ["jeanne"],
                "ower_weights": [1.0],
            },
            {
                "date": "2016-12-31",
                "bill_type": "Expense",
                "what": "red wine",
                "amount": 200.0,
                "currency": "XXX",
                "payer_name": "jeanne",
                "payer_weight": 1.0,
                "owers": ["zorglub", "tata"],
                "ower_weights": [2.0, 1.0],
            },
            {
                "date": "2016-12-31",
                "bill_type": "Expense",
                "what": "\xe0 raclette",
                "amount": 10.0,
                "currency": "XXX",
                "payer_name": "zorglub",
                "payer_weight": 2.0,
                "owers": ["zorglub", "jeanne", "tata", "p\xe9p\xe9"],
                "ower_weights": [2.0, 1.0, 1.0, 1.0],
            },
        ]
        assert json.loads(resp.data.decode("utf-8")) == expected

        # generate csv export of bills
        resp = self.client.get("/raclette/export/bills.csv")
        expected = [
            "date,what,bill_type,amount,currency,payer_name,payer_weight,owers,ower_weights",
            "2017-01-01,refund,Reimbursement,XXX,13.33,tata,1.0,jeanne,1.0",
            '2016-12-31,red wine,Expense,XXX,200.0,jeanne,1.0,"zorglub, tata","2.0, 1.0"',
            '2016-12-31,à raclette,Expense,10.0,XXX,zorglub,2.0,"zorglub, jeanne, tata, pépé","2.0, 1.0, 1.0, 1.0"',
        ]
        received_lines = resp.data.decode("utf-8").split("\n")

        for i, line in enumerate(expected):
            assert set(line.split(",")) == set(received_lines[i].strip("\r").split(","))

        # generate json export of transactions
        resp = self.client.get("/raclette/export/transactions.json")
        expected = [
            {
                "amount": 2.00,
                "currency": "XXX",
                "receiver": "jeanne",
                "ower": "p\xe9p\xe9",
            },
            {"amount": 55.34, "currency": "XXX", "receiver": "jeanne", "ower": "tata"},
            {
                "amount": 127.33,
                "currency": "XXX",
                "receiver": "jeanne",
                "ower": "zorglub",
            },
        ]

        assert json.loads(resp.data.decode("utf-8")) == expected

        # generate csv export of transactions
        resp = self.client.get("/raclette/export/transactions.csv")

        expected = [
            "amount,currency,receiver,ower",
            "2.0,XXX,jeanne,pépé",
            "55.34,XXX,jeanne,tata",
            "127.33,XXX,jeanne,zorglub",
        ]
        received_lines = resp.data.decode("utf-8").split("\n")

        for i, line in enumerate(expected):
            assert set(line.split(",")) == set(received_lines[i].strip("\r").split(","))

        # wrong export_format should return a 404
        resp = self.client.get("/raclette/export/transactions.wrong")
        assert resp.status_code == 404

    @pytest.mark.skip(reason="Currency conversion is broken")
    def test_export_with_currencies(self):
        self.post_project("raclette", default_currency="EUR")

        # add participants
        self.client.post("/raclette/members/add", data={"name": "zorglub", "weight": 2})
        self.client.post("/raclette/members/add", data={"name": "jeanne"})
        self.client.post("/raclette/members/add", data={"name": "tata"})
        self.client.post("/raclette/members/add", data={"name": "pépé"})

        # create bills
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "à raclette",
                "bill_type": "Expense",
                "payer": 1,
                "payed_for": [1, 2, 3, 4],
                "amount": "10.0",
                "original_currency": "EUR",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "poutine from Québec",
                "bill_type": "Expense",
                "payer": 2,
                "payed_for": [1, 3],
                "amount": "100",
                "original_currency": "CAD",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2017-01-01",
                "what": "refund",
                "bill_type": "Reimbursement",
                "payer": 3,
                "payed_for": [2],
                "amount": "13.33",
                "original_currency": "EUR",
            },
        )

        # generate json export of bills
        resp = self.client.get("/raclette/export/bills.json")
        expected = [
            {
                "date": "2017-01-01",
                "what": "refund",
                "bill_type": "Reimbursement",
                "amount": 13.33,
                "currency": "EUR",
                "payer_name": "tata",
                "payer_weight": 1.0,
                "owers": ["jeanne"],
            },
            {
                "date": "2016-12-31",
                "what": "poutine from Qu\xe9bec",
                "bill_type": "Expense",
                "amount": 100.0,
                "currency": "CAD",
                "payer_name": "jeanne",
                "payer_weight": 1.0,
                "owers": ["zorglub", "tata"],
            },
            {
                "date": "2016-12-31",
                "what": "fromage \xe0 raclette",
                "bill_type": "Expense",
                "amount": 10.0,
                "currency": "EUR",
                "payer_name": "zorglub",
                "payer_weight": 2.0,
                "owers": ["zorglub", "jeanne", "tata", "p\xe9p\xe9"],
            },
        ]
        assert json.loads(resp.data.decode("utf-8")) == expected

        # generate csv export of bills
        resp = self.client.get("/raclette/export/bills.csv")
        expected = [
            "date,what,bill_type,amount,currency,payer_name,payer_weight,owers",
            "2017-01-01,refund,Reimbursement,13.33,EUR,tata,1.0,jeanne",
            '2016-12-31,poutine from Québec,Expense,100.0,CAD,jeanne,1.0,"zorglub, tata"',
            '2016-12-31,à raclette,Expense,10.0,EUR,zorglub,2.0,"zorglub, jeanne, tata, pépé"',
        ]
        received_lines = resp.data.decode("utf-8").split("\n")

        for i, line in enumerate(expected):
            assert set(line.split(",")) == set(received_lines[i].strip("\r").split(","))

        # generate json export of transactions (in EUR!)
        resp = self.client.get("/raclette/export/transactions.json")
        expected = [
            {
                "amount": 2.00,
                "currency": "EUR",
                "receiver": "jeanne",
                "ower": "p\xe9p\xe9",
            },
            {"amount": 10.89, "currency": "EUR", "receiver": "jeanne", "ower": "tata"},
            {
                "amount": 38.45,
                "currency": "EUR",
                "receiver": "jeanne",
                "ower": "zorglub",
            },
        ]

        assert json.loads(resp.data.decode("utf-8")) == expected

        # generate csv export of transactions
        resp = self.client.get("/raclette/export/transactions.csv")

        expected = [
            "amount,currency,receiver,ower",
            "2.0,EUR,jeanne,pépé",
            "10.89,EUR,jeanne,tata",
            "38.45,EUR,jeanne,zorglub",
        ]
        received_lines = resp.data.decode("utf-8").split("\n")

        for i, line in enumerate(expected):
            assert set(line.split(",")) == set(received_lines[i].strip("\r").split(","))

        # Change project currency to CAD
        project = self.get_project("raclette")
        project.switch_currency("CAD")

        # generate json export of transactions (now in CAD!)
        resp = self.client.get("/raclette/export/transactions.json")
        expected = [
            {
                "amount": 3.00,
                "currency": "CAD",
                "receiver": "jeanne",
                "ower": "p\xe9p\xe9",
            },
            {"amount": 16.34, "currency": "CAD", "receiver": "jeanne", "ower": "tata"},
            {
                "amount": 57.67,
                "currency": "CAD",
                "receiver": "jeanne",
                "ower": "zorglub",
            },
        ]

        assert json.loads(resp.data.decode("utf-8")) == expected

        # generate csv export of transactions
        resp = self.client.get("/raclette/export/transactions.csv")

        expected = [
            "amount,currency,receiver,ower",
            "3.0,CAD,jeanne,pépé",
            "16.34,CAD,jeanne,tata",
            "57.67,CAD,jeanne,zorglub",
        ]
        received_lines = resp.data.decode("utf-8").split("\n")

        for i, line in enumerate(expected):
            assert set(line.split(",")) == set(received_lines[i].strip("\r").split(","))

    def test_export_escape_formulae(self):
        self.post_project("raclette", default_currency="EUR")

        # add participants
        self.client.post("/raclette/members/add", data={"name": "zorglub"})

        # create bills
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "=COS(36)",
                "bill_type": "Expense",
                "payer": 1,
                "payed_for": [1],
                "amount": "10.0",
                "original_currency": "EUR",
            },
        )

        # generate csv export of bills
        resp = self.client.get("/raclette/export/bills.csv")
        expected = [
            "date,what,bill_type,amount,currency,payer_name,payer_weight,owers,ower_weights",
            "2016-12-31,'=COS(36),Expense,10.0,EUR,zorglub,1.0,zorglub,1.0",
        ]
        received_lines = resp.data.decode("utf-8").split("\n")

        for i, line in enumerate(expected):
            assert set(line.split(",")) == set(received_lines[i].strip("\r").split(","))


@pytest.mark.usefixtures("import_data_6_0")
class TestImportJSON60(CommonTestCase.Import):
    def generate_form_data(self, data):
        return {"file": (list_of_dicts2json(data), "test.json")}


@pytest.mark.usefixtures("import_data_7_0")
class TestImportJSON70(CommonTestCase.Import):
    def generate_form_data(self, data):
        return {"file": (list_of_dicts2json(data), "test.json")}


@pytest.mark.usefixtures("import_data_6_0")
class TestImportCSV60(CommonTestCase.Import):
    def generate_form_data(self, data):
        formatted_data = copy.deepcopy(data)
        for d in formatted_data:
            d["owers"] = ", ".join([o for o in d.get("owers", [])])
        return {"file": (list_of_dicts2csv(formatted_data), "test.csv")}


@pytest.mark.usefixtures("import_data_7_0")
class TestImportCSV70(CommonTestCase.Import):
    def generate_form_data(self, data):
        formatted_data = copy.deepcopy(data)
        for d in formatted_data:
            d["owers"] = ", ".join([o for o in d.get("owers", [])])
        return {"file": (list_of_dicts2csv(formatted_data), "test.csv")}


class TestImportOwerWeights(IhatemoneyTestCase):
    """Export/import round trips keep ower weights (issue #1481)."""

    def create_weighted_project(self, project_id):
        self.post_project(project_id)

        # Alice weighs 2 but never pays; Bob weighs 1 and pays.
        self.client.post(
            f"/{project_id}/members/add", data={"name": "Alice", "weight": 2}
        )
        self.client.post(f"/{project_id}/members/add", data={"name": "Bob"})
        self.client.post(
            f"/{project_id}/add",
            data={
                "date": "2026-11-01",
                "bill_type": "Expense",
                "what": "Groceries",
                "payer": 2,
                "payed_for": [1, 2],
                "amount": "30",
            },
        )

    def import_file(self, project_id, filename, data):
        self.post_project(project_id)
        self.login(project_id)
        self.import_project(project_id, {"file": (data, filename)})

    def member_weights(self, project_id):
        project = self.get_project(project_id)
        return {m.name: m.weight for m in project.members}

    def member_balances(self, project_id):
        project = self.get_project(project_id)
        return {m.name: project.balance[m.id] for m in project.members}

    def test_json_round_trip_keeps_ower_weight(self):
        self.create_weighted_project("groceries")
        resp = self.client.get("/groceries/export/bills.json")
        exported = json.loads(resp.data.decode("utf-8"))
        assert exported[0]["ower_weights"] == [2.0, 1.0]

        self.import_file("groceries2", "test.json", list_of_dicts2json(exported))

        assert self.member_weights("groceries2") == {"Alice": 2.0, "Bob": 1.0}
        assert self.member_balances("groceries2") == {"Alice": -20.0, "Bob": 20.0}

    def test_csv_round_trip_keeps_ower_weight(self):
        self.create_weighted_project("groceries")
        resp = self.client.get("/groceries/export/bills.csv")
        rows = list(csv.DictReader(io.StringIO(resp.data.decode("utf-8"))))
        assert rows[0]["ower_weights"] == "2.0, 1.0"

        self.import_file("groceries2", "test.csv", io.BytesIO(resp.data))

        assert self.member_weights("groceries2") == {"Alice": 2.0, "Bob": 1.0}
        assert self.member_balances("groceries2") == {"Alice": -20.0, "Bob": 20.0}

    def test_import_twice_does_not_duplicate_bills(self):
        # Ower order in dedupe is #1483's scope; a single ower keeps the
        # comparison order-free, so this pins that ower_weights itself
        # does not break dedupe.
        self.post_project("groceries")
        self.client.post("/groceries/members/add", data={"name": "Alice", "weight": 2})
        self.client.post("/groceries/members/add", data={"name": "Bob"})
        self.client.post(
            "/groceries/add",
            data={
                "date": "2026-11-01",
                "bill_type": "Expense",
                "what": "Groceries",
                "payer": 2,
                "payed_for": [1],
                "amount": "30",
            },
        )
        resp = self.client.get("/groceries/export/bills.json")
        exported = json.loads(resp.data.decode("utf-8"))

        self.import_file("groceries2", "test.json", list_of_dicts2json(exported))
        self.import_file("groceries2", "test.json", list_of_dicts2json(exported))

        project = self.get_project("groceries2")
        assert len(project.get_pretty_bills()) == 1
        assert self.member_weights("groceries2") == {"Alice": 2.0, "Bob": 1.0}

    def test_old_format_import_gives_weight_one(self):
        # Files exported before ower_weights existed carry no weights
        # for owers; everyone but the payer falls back to 1.
        data = [
            {
                "date": "2026-11-01",
                "what": "Groceries",
                "amount": 30.0,
                "bill_type": "Expense",
                "currency": "XXX",
                "payer_name": "Bob",
                "payer_weight": 1.0,
                "owers": ["Alice", "Bob"],
            }
        ]
        self.import_file("groceries", "test.json", list_of_dicts2json(data))

        assert self.member_weights("groceries") == {"Alice": 1.0, "Bob": 1.0}


class TestGetMembers:
    def bill(self, owers, payer_name="Bob", payer_weight=1.0, ower_weights=None):
        bill = {
            "payer_name": payer_name,
            "payer_weight": payer_weight,
            "owers": owers,
        }
        if ower_weights is not None:
            bill["ower_weights"] = ower_weights
        return bill

    def test_missing_ower_weights_falls_back_to_one(self):
        members = get_members([self.bill(["Alice", "Bob"])])
        assert members == [("Bob", 1.0), ("Alice", 1)]

    def test_length_mismatch_falls_back_whole_bill(self):
        members = get_members([self.bill(["Alice", "Bob"], ower_weights=[2.0])])
        assert members == [("Bob", 1.0), ("Alice", 1)]
        members = get_members([self.bill(["Alice"], ower_weights=[2.0, 3.0])])
        assert members == [("Bob", 1.0), ("Alice", 1)]

    def test_invalid_entry_falls_back_to_one_for_that_entry(self):
        for bad in ["x", 0, -1, float("nan"), float("inf"), True, None]:
            members = get_members(
                [self.bill(["Alice", "Bob"], ower_weights=[2.0, bad])]
            )
            assert members == [("Bob", 1.0), ("Alice", 2.0)]

    def test_csv_string_weights_are_parsed(self):
        members = get_members([self.bill(["Alice", "Bob"], ower_weights="2.0, 1.0")])
        assert members == [("Bob", 1.0), ("Alice", 2.0)]

    def test_payer_weight_wins_over_ower_weight(self):
        members = get_members(
            [
                self.bill(["Alice"], ower_weights=[2.0]),
                self.bill(["Bob"], payer_name="Alice", payer_weight=1.0),
            ]
        )
        assert members == [("Bob", 1.0), ("Alice", 1.0)]
