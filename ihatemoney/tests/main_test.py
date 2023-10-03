import os
import smtplib
import socket
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import orm
from werkzeug.security import check_password_hash

from ihatemoney import models
from ihatemoney.currency_convertor import CurrencyConverter
from ihatemoney.manage import delete_project, generate_config, password_hash
from ihatemoney.run import load_configuration
from ihatemoney.tests.common.ihatemoney_testcase import BaseTestCase, IhatemoneyTestCase

# Unset configuration file env var if previously set
os.environ.pop("IHATEMONEY_SETTINGS_FILE_PATH", None)

__HERE__ = os.path.dirname(os.path.abspath(__file__))


class TestConfiguration(BaseTestCase):
    def test_default_configuration(self):
        """Test that default settings are loaded when no other configuration file is specified"""
        assert not self.app.config["DEBUG"]
        assert not self.app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]
        assert self.app.config["MAIL_DEFAULT_SENDER"] == (
            "Budget manager <admin@example.com>"
        )
        assert self.app.config["ACTIVATE_DEMO_PROJECT"]
        assert self.app.config["ALLOW_PUBLIC_PROJECT_CREATION"]
        assert not self.app.config["ACTIVATE_ADMIN_DASHBOARD"]
        assert not self.app.config["ENABLE_CAPTCHA"]

    def test_env_var_configuration_file(self):
        """Test that settings are loaded from a configuration file specified
        with an environment variable."""
        os.environ["IHATEMONEY_SETTINGS_FILE_PATH"] = os.path.join(
            __HERE__, "ihatemoney_envvar.cfg"
        )
        load_configuration(self.app)
        assert self.app.config["SECRET_KEY"] == "lalatra"

        # Test that the specified configuration file is loaded
        # even if the default configuration file ihatemoney.cfg exists
        # in the current directory.
        os.environ["IHATEMONEY_SETTINGS_FILE_PATH"] = os.path.join(
            __HERE__, "ihatemoney_envvar.cfg"
        )
        self.app.config.root_path = __HERE__
        load_configuration(self.app)
        assert self.app.config["SECRET_KEY"] == "lalatra"

        os.environ.pop("IHATEMONEY_SETTINGS_FILE_PATH", None)

    def test_default_configuration_file(self):
        """Test that settings are loaded from a configuration file if one is found
        in the current directory."""
        self.app.config.root_path = __HERE__
        load_configuration(self.app)
        assert self.app.config["SECRET_KEY"] == "supersecret"


class TestServer(IhatemoneyTestCase):
    def test_homepage(self):
        # See https://github.com/spiral-project/ihatemoney/pull/358
        self.app.config["APPLICATION_ROOT"] = "/"
        req = self.client.get("/")
        self.assertStatus(200, req)

    def test_unprefixed(self):
        self.app.config["APPLICATION_ROOT"] = "/"
        req = self.client.get("/foo/")
        self.assertStatus(303, req)

    def test_prefixed(self):
        self.app.config["APPLICATION_ROOT"] = "/foo"
        req = self.client.get("/foo/")
        self.assertStatus(200, req)


class TestCommand(BaseTestCase):
    def test_generate_config(self):
        """Simply checks that all config file generation
        - raise no exception
        - produce something non-empty
        """
        runner = self.app.test_cli_runner()
        for config_file in generate_config.params[0].type.choices:
            result = runner.invoke(generate_config, config_file)
            assert len(result.output.strip()) != 0

    def test_generate_password_hash(self):
        runner = self.app.test_cli_runner()
        with patch("getpass.getpass", new=lambda prompt: "secret"):
            result = runner.invoke(password_hash)
            assert check_password_hash(result.output.strip(), "secret")

    def test_demo_project_deletion(self):
        self.create_project("demo")
        assert self.get_project("demo").name == "demo"

        runner = self.app.test_cli_runner()
        runner.invoke(delete_project, "demo")

        assert len(models.Project.query.all()) == 0


class TestModels(IhatemoneyTestCase):
    def test_weighted_bills(self):
        """Test the SQL request that fetch all bills and weights"""
        self.post_project("raclette")

        # add members
        self.client.post("/raclette/members/add", data={"name": "zorglub", "weight": 2})
        self.client.post("/raclette/members/add", data={"name": "fred"})
        self.client.post("/raclette/members/add", data={"name": "tata"})
        # Add a member with a balance=0 :
        self.client.post("/raclette/members/add", data={"name": "pépé"})

        # create bills
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1, 2, 3],
                "amount": "10.0",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "red wine",
                "payer": 2,
                "payed_for": [1],
                "amount": "20",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "delicatessen",
                "payer": 1,
                "payed_for": [1, 2],
                "amount": "10",
            },
        )
        project = models.Project.query.get_by_name(name="raclette")
        for weight, bill in project.get_bill_weights().all():
            if bill.what == "red wine":
                pay_each_expected = 20 / 2
                assert bill.amount / weight == pay_each_expected
            if bill.what == "fromage à raclette":
                pay_each_expected = 10 / 4
                assert bill.amount / weight == pay_each_expected
            if bill.what == "delicatessen":
                pay_each_expected = 10 / 3
                assert bill.amount / weight == pay_each_expected

    def test_bill_pay_each(self):
        self.post_project("raclette")

        # add members
        self.client.post("/raclette/members/add", data={"name": "zorglub", "weight": 2})
        self.client.post("/raclette/members/add", data={"name": "fred"})
        self.client.post("/raclette/members/add", data={"name": "tata"})
        # Add a member with a balance=0 :
        self.client.post("/raclette/members/add", data={"name": "pépé"})

        # create bills
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1, 2, 3],
                "amount": "10.0",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "red wine",
                "payer": 2,
                "payed_for": [1],
                "amount": "20",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "delicatessen",
                "payer": 1,
                "payed_for": [1, 2],
                "amount": "10",
            },
        )

        project = models.Project.query.get_by_name(name="raclette")
        zorglub = models.Person.query.get_by_name(name="zorglub", project=project)
        zorglub_bills = models.Bill.query.options(
            orm.subqueryload(models.Bill.owers)
        ).filter(models.Bill.owers.contains(zorglub))
        for bill in zorglub_bills.all():
            if bill.what == "red wine":
                pay_each_expected = 20 / 2
                assert bill.pay_each() == pay_each_expected
            if bill.what == "fromage à raclette":
                pay_each_expected = 10 / 4
                assert bill.pay_each() == pay_each_expected
            if bill.what == "delicatessen":
                pay_each_expected = 10 / 3
                assert bill.pay_each() == pay_each_expected


class TestEmailFailure(IhatemoneyTestCase):
    def test_creation_email_failure_smtp(self):
        self.login("raclette")
        with patch.object(
            self.app.mail, "send", MagicMock(side_effect=smtplib.SMTPException)
        ):
            resp = self.post_project("raclette")
        # Check that an error message is displayed
        assert (
            "We tried to send you an reminder email, but there was an error"
            in resp.data.decode("utf-8")
        )
        # Check that we were redirected to the home page anyway
        assert (
            '<a href="/raclette/members/add">Add the first participant'
            in resp.data.decode("utf-8")
        )

    def test_creation_email_failure_socket(self):
        self.login("raclette")
        with patch.object(self.app.mail, "send", MagicMock(side_effect=socket.error)):
            resp = self.post_project("raclette")
        # Check that an error message is displayed
        assert (
            "We tried to send you an reminder email, but there was an error"
            in resp.data.decode("utf-8")
        )
        # Check that we were redirected to the home page anyway
        assert (
            '<a href="/raclette/members/add">Add the first participant'
            in resp.data.decode("utf-8")
        )

    def test_password_reset_email_failure(self):
        self.create_project("raclette")
        for exception in (smtplib.SMTPException, socket.error):
            with patch.object(self.app.mail, "send", MagicMock(side_effect=exception)):
                resp = self.client.post(
                    "/password-reminder", data={"id": "raclette"}, follow_redirects=True
                )
            # Check that an error message is displayed
            assert "there was an error while sending you an email" in resp.data.decode(
                "utf-8"
            )
            # Check that we were not redirected to the success page
            assert (
                "A link to reset your password has been sent to you"
                not in resp.data.decode("utf-8")
            )

    def test_invitation_email_failure(self):
        self.login("raclette")
        self.post_project("raclette")
        for exception in (smtplib.SMTPException, socket.error):
            with patch.object(self.app.mail, "send", MagicMock(side_effect=exception)):
                resp = self.client.post(
                    "/raclette/invite",
                    data={"emails": "toto@notmyidea.org"},
                    follow_redirects=True,
                )
            # Check that an error message is displayed
            assert (
                "there was an error while trying to send the invitation emails"
                in resp.data.decode("utf-8")
            )
            # Check that we are still on the same page (no redirection)
            assert "Invite people to join this project" in resp.data.decode("utf-8")


class TestCaptcha(IhatemoneyTestCase):
    ENABLE_CAPTCHA = True

    def test_project_creation_with_captcha_case_insensitive(self):
        # Test that case doesn't matter
        # Patch the lazy_gettext as it is imported as '_' in forms for captcha value check
        with patch("ihatemoney.forms._", new=lambda x: "ÉÙÜẞ"), self.client as c:
            c.post(
                "/create",
                data={
                    "name": "raclette party",
                    "id": "raclette",
                    "password": "party",
                    "contact_email": "raclette@notmyidea.org",
                    "default_currency": "USD",
                    "captcha": "éùüß",
                },
            )
            assert len(models.Project.query.all()) == 1

    def test_project_creation_with_captcha(self):
        with self.client as c:
            c.post(
                "/create",
                data={
                    "name": "raclette party",
                    "id": "raclette",
                    "password": "party",
                    "contact_email": "raclette@notmyidea.org",
                    "default_currency": "USD",
                },
            )
            assert len(models.Project.query.all()) == 0

            c.post(
                "/create",
                data={
                    "name": "raclette party",
                    "id": "raclette",
                    "password": "party",
                    "contact_email": "raclette@notmyidea.org",
                    "default_currency": "USD",
                    "captcha": "nope",
                },
            )
            assert len(models.Project.query.all()) == 0

            c.post(
                "/create",
                data={
                    "name": "raclette party",
                    "id": "raclette",
                    "password": "party",
                    "contact_email": "raclette@notmyidea.org",
                    "default_currency": "USD",
                    "captcha": "euro",
                },
            )
            assert len(models.Project.query.all()) == 1

    def test_api_project_creation_does_not_need_captcha(self):
        self.client.get("/")
        resp = self.client.post(
            "/api/projects",
            data={
                "name": "raclette",
                "id": "raclette",
                "password": "raclette",
                "contact_email": "raclette@notmyidea.org",
            },
        )
        assert resp.status_code == 201
        assert len(models.Project.query.all()) == 1


class TestCurrencyConverter:
    converter = CurrencyConverter()
    mock_data = {
        "USD": 1,
        "EUR": 0.8,
        "CAD": 1.2,
        "PLN": 4,
        CurrencyConverter.no_currency: 1,
    }
    converter.get_rates = MagicMock(return_value=mock_data)

    def test_only_one_instance(self):
        one = id(CurrencyConverter())
        two = id(CurrencyConverter())
        assert one == two

    def test_get_currencies(self):
        currencies = self.converter.get_currencies()
        for currency in ["USD", "EUR", "CAD", "PLN", CurrencyConverter.no_currency]:
            assert currency in currencies

    def test_exchange_currency(self):
        result = self.converter.exchange_currency(100, "USD", "EUR")
        assert result == 80.0

    def test_failing_remote(self):
        rates = {}
        with patch("requests.Response.json", new=lambda _: {}), pytest.warns(
            UserWarning
        ):
            # we need a non-patched converter, but it seems that MagickMock
            # is mocking EVERY instance of the class method. Too bad.
            rates = CurrencyConverter.get_rates(self.converter)
        assert rates == {CurrencyConverter.no_currency: 1}
