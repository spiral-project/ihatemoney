import copy
import json

import pytest

from ihatemoney.tests.common.ihatemoney_testcase import IhatemoneyTestCase
from ihatemoney.utils import list_of_dicts2csv, list_of_dicts2json


@pytest.fixture
def import_data(request: pytest.FixtureRequest):
    data = [
        {
            "date": "2017-01-01",
            "what": "refund",
            "amount": 13.33,
            "payer_name": "tata",
            "payer_weight": 1.0,
            "owers": ["fred"],
        },
        {
            "date": "2016-12-31",
            "what": "red wine",
            "amount": 200.0,
            "payer_name": "fred",
            "payer_weight": 1.0,
            "owers": ["zorglub", "tata"],
        },
        {
            "date": "2016-12-31",
            "what": "fromage a raclette",
            "amount": 10.0,
            "payer_name": "zorglub",
            "payer_weight": 2.0,
            "owers": ["zorglub", "fred", "tata", "pepe"],
        },
    ]
    request.cls.data = data
    yield data


class CommonTestCase(object):
    @pytest.mark.usefixtures("import_data")
    class Import(IhatemoneyTestCase):
        def setUp(self):
            super().setUp()
            self.data = [
                {
                    "date": "2017-01-01",
                    "what": "refund",
                    "amount": 13.33,
                    "payer_name": "tata",
                    "payer_weight": 1.0,
                    "owers": ["fred"],
                },
                {
                    "date": "2016-12-31",
                    "what": "red wine",
                    "amount": 200.0,
                    "payer_name": "fred",
                    "payer_weight": 1.0,
                    "owers": ["zorglub", "tata"],
                },
                {
                    "date": "2016-12-31",
                    "what": "fromage a raclette",
                    "amount": 10.0,
                    "payer_name": "zorglub",
                    "payer_weight": 2.0,
                    "owers": ["zorglub", "fred", "tata", "pepe"],
                },
            ]

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
            self.client.post("/raclette/members/add", data={"name": "fred"})
            self.client.post("/raclette/members/add", data={"name": "tata"})
            self.client.post(
                "/raclette/add",
                data={
                    "date": "2016-12-31",
                    "what": "red wine",
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
                    "payer_name": "tata",
                    "payer_weight": 1.0,
                    "owers": ["fred"],
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
        self.client.post("/raclette/members/add", data={"name": "fred"})
        self.client.post("/raclette/members/add", data={"name": "tata"})
        self.client.post("/raclette/members/add", data={"name": "pépé"})

        # create bills
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1, 2, 3, 4],
                "amount": "10.0",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
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
                "what": "refund",
                "amount": 13.33,
                "currency": "XXX",
                "payer_name": "tata",
                "payer_weight": 1.0,
                "owers": ["fred"],
            },
            {
                "date": "2016-12-31",
                "what": "red wine",
                "amount": 200.0,
                "currency": "XXX",
                "payer_name": "fred",
                "payer_weight": 1.0,
                "owers": ["zorglub", "tata"],
            },
            {
                "date": "2016-12-31",
                "what": "fromage \xe0 raclette",
                "amount": 10.0,
                "currency": "XXX",
                "payer_name": "zorglub",
                "payer_weight": 2.0,
                "owers": ["zorglub", "fred", "tata", "p\xe9p\xe9"],
            },
        ]
        assert json.loads(resp.data.decode("utf-8")) == expected

        # generate csv export of bills
        resp = self.client.get("/raclette/export/bills.csv")
        expected = [
            "date,what,amount,currency,payer_name,payer_weight,owers",
            "2017-01-01,refund,XXX,13.33,tata,1.0,fred",
            '2016-12-31,red wine,XXX,200.0,fred,1.0,"zorglub, tata"',
            '2016-12-31,fromage à raclette,10.0,XXX,zorglub,2.0,"zorglub, fred, tata, pépé"',
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
                "receiver": "fred",
                "ower": "p\xe9p\xe9",
            },
            {"amount": 55.34, "currency": "XXX", "receiver": "fred", "ower": "tata"},
            {
                "amount": 127.33,
                "currency": "XXX",
                "receiver": "fred",
                "ower": "zorglub",
            },
        ]

        assert json.loads(resp.data.decode("utf-8")) == expected

        # generate csv export of transactions
        resp = self.client.get("/raclette/export/transactions.csv")

        expected = [
            "amount,currency,receiver,ower",
            "2.0,XXX,fred,pépé",
            "55.34,XXX,fred,tata",
            "127.33,XXX,fred,zorglub",
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
        self.client.post("/raclette/members/add", data={"name": "fred"})
        self.client.post("/raclette/members/add", data={"name": "tata"})
        self.client.post("/raclette/members/add", data={"name": "pépé"})

        # create bills
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "fromage à raclette",
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
                "amount": 13.33,
                "currency": "EUR",
                "payer_name": "tata",
                "payer_weight": 1.0,
                "owers": ["fred"],
            },
            {
                "date": "2016-12-31",
                "what": "poutine from Qu\xe9bec",
                "amount": 100.0,
                "currency": "CAD",
                "payer_name": "fred",
                "payer_weight": 1.0,
                "owers": ["zorglub", "tata"],
            },
            {
                "date": "2016-12-31",
                "what": "fromage \xe0 raclette",
                "amount": 10.0,
                "currency": "EUR",
                "payer_name": "zorglub",
                "payer_weight": 2.0,
                "owers": ["zorglub", "fred", "tata", "p\xe9p\xe9"],
            },
        ]
        assert json.loads(resp.data.decode("utf-8")) == expected

        # generate csv export of bills
        resp = self.client.get("/raclette/export/bills.csv")
        expected = [
            "date,what,amount,currency,payer_name,payer_weight,owers",
            "2017-01-01,refund,13.33,EUR,tata,1.0,fred",
            '2016-12-31,poutine from Québec,100.0,CAD,fred,1.0,"zorglub, tata"',
            '2016-12-31,fromage à raclette,10.0,EUR,zorglub,2.0,"zorglub, fred, tata, pépé"',
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
                "receiver": "fred",
                "ower": "p\xe9p\xe9",
            },
            {"amount": 10.89, "currency": "EUR", "receiver": "fred", "ower": "tata"},
            {"amount": 38.45, "currency": "EUR", "receiver": "fred", "ower": "zorglub"},
        ]

        assert json.loads(resp.data.decode("utf-8")) == expected

        # generate csv export of transactions
        resp = self.client.get("/raclette/export/transactions.csv")

        expected = [
            "amount,currency,receiver,ower",
            "2.0,EUR,fred,pépé",
            "10.89,EUR,fred,tata",
            "38.45,EUR,fred,zorglub",
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
                "receiver": "fred",
                "ower": "p\xe9p\xe9",
            },
            {"amount": 16.34, "currency": "CAD", "receiver": "fred", "ower": "tata"},
            {"amount": 57.67, "currency": "CAD", "receiver": "fred", "ower": "zorglub"},
        ]

        assert json.loads(resp.data.decode("utf-8")) == expected

        # generate csv export of transactions
        resp = self.client.get("/raclette/export/transactions.csv")

        expected = [
            "amount,currency,receiver,ower",
            "3.0,CAD,fred,pépé",
            "16.34,CAD,fred,tata",
            "57.67,CAD,fred,zorglub",
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
                "payer": 1,
                "payed_for": [1],
                "amount": "10.0",
                "original_currency": "EUR",
            },
        )

        # generate csv export of bills
        resp = self.client.get("/raclette/export/bills.csv")
        expected = [
            "date,what,amount,currency,payer_name,payer_weight,owers",
            "2016-12-31,'=COS(36),10.0,EUR,zorglub,1.0,zorglub",
        ]
        received_lines = resp.data.decode("utf-8").split("\n")

        for i, line in enumerate(expected):
            assert set(line.split(",")) == set(received_lines[i].strip("\r").split(","))


class TestImportJSON(CommonTestCase.Import):
    def generate_form_data(self, data):
        return {"file": (list_of_dicts2json(data), "test.json")}


class TestImportCSV(CommonTestCase.Import):
    def generate_form_data(self, data):
        formatted_data = copy.deepcopy(data)
        for d in formatted_data:
            d["owers"] = ", ".join([o for o in d.get("owers", [])])
        return {"file": (list_of_dicts2csv(formatted_data), "test.csv")}
