import os
import smtplib
import socket
import unittest
from unittest.mock import MagicMock, patch

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


class ConfigurationTestCase(BaseTestCase):
    def test_default_configuration(self):
        """Test that default settings are loaded when no other configuration file is specified"""
        self.assertFalse(self.app.config["DEBUG"])
        self.assertFalse(self.app.config["SQLALCHEMY_TRACK_MODIFICATIONS"])
        self.assertEqual(
            self.app.config["MAIL_DEFAULT_SENDER"],
            ("Budget manager <admin@example.com>"),
        )
        self.assertTrue(self.app.config["ACTIVATE_DEMO_PROJECT"])
        self.assertTrue(self.app.config["ALLOW_PUBLIC_PROJECT_CREATION"])
        self.assertFalse(self.app.config["ACTIVATE_ADMIN_DASHBOARD"])
        self.assertFalse(self.app.config["ENABLE_CAPTCHA"])

    def test_env_var_configuration_file(self):
        """Test that settings are loaded from a configuration file specified
        with an environment variable."""
        os.environ["IHATEMONEY_SETTINGS_FILE_PATH"] = os.path.join(
            __HERE__, "ihatemoney_envvar.cfg"
        )
        load_configuration(self.app)
        self.assertEqual(self.app.config["SECRET_KEY"], "lalatra")

        # Test that the specified configuration file is loaded
        # even if the default configuration file ihatemoney.cfg exists
        # in the current directory.
        os.environ["IHATEMONEY_SETTINGS_FILE_PATH"] = os.path.join(
            __HERE__, "ihatemoney_envvar.cfg"
        )
        self.app.config.root_path = __HERE__
        load_configuration(self.app)
        self.assertEqual(self.app.config["SECRET_KEY"], "lalatra")

        os.environ.pop("IHATEMONEY_SETTINGS_FILE_PATH", None)

    def test_default_configuration_file(self):
        """Test that settings are loaded from a configuration file if one is found
        in the current directory."""
        self.app.config.root_path = __HERE__
        load_configuration(self.app)
        self.assertEqual(self.app.config["SECRET_KEY"], "supersecret")


class ServerTestCase(IhatemoneyTestCase):
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


class CommandTestCase(BaseTestCase):
    def test_generate_config(self):
        """Simply checks that all config file generation
        - raise no exception
        - produce something non-empty
        """
        runner = self.app.test_cli_runner()
        for config_file in generate_config.params[0].type.choices:
            result = runner.invoke(generate_config, config_file)
            self.assertNotEqual(len(result.output.strip()), 0)

    def test_generate_password_hash(self):
        runner = self.app.test_cli_runner()
        with patch("getpass.getpass", new=lambda prompt: "secret"):
            result = runner.invoke(password_hash)
            self.assertTrue(check_password_hash(result.output.strip(), "secret"))

    def test_demo_project_deletion(self):
        self.create_project("demo")
        self.assertEqual(self.get_project("demo").name, "demo")

        runner = self.app.test_cli_runner()
        runner.invoke(delete_project, "demo")

        self.assertEqual(len(models.Project.query.all()), 0)


class ModelsTestCase(IhatemoneyTestCase):
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
                self.assertEqual(bill.amount / weight, pay_each_expected)
            if bill.what == "fromage à raclette":
                pay_each_expected = 10 / 4
                self.assertEqual(bill.amount / weight, pay_each_expected)
            if bill.what == "delicatessen":
                pay_each_expected = 10 / 3
                self.assertEqual(bill.amount / weight, pay_each_expected)

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
                self.assertEqual(bill.pay_each(), pay_each_expected)
            if bill.what == "fromage à raclette":
                pay_each_expected = 10 / 4
                self.assertEqual(bill.pay_each(), pay_each_expected)
            if bill.what == "delicatessen":
                pay_each_expected = 10 / 3
                self.assertEqual(bill.pay_each(), pay_each_expected)


class EmailFailureTestCase(IhatemoneyTestCase):
    def test_creation_email_failure_smtp(self):
        self.login("raclette")
        with patch.object(
            self.app.mail, "send", MagicMock(side_effect=smtplib.SMTPException)
        ):
            resp = self.post_project("raclette")
        # Check that an error message is displayed
        self.assertIn(
            "We tried to send you an reminder email, but there was an error",
            resp.data.decode("utf-8"),
        )
        # Check that we were redirected to the home page anyway
        self.assertIn(
            'You probably want to <a href="/raclette/members/add"',
            resp.data.decode("utf-8"),
        )

    def test_creation_email_failure_socket(self):
        self.login("raclette")
        with patch.object(self.app.mail, "send", MagicMock(side_effect=socket.error)):
            resp = self.post_project("raclette")
        # Check that an error message is displayed
        self.assertIn(
            "We tried to send you an reminder email, but there was an error",
            resp.data.decode("utf-8"),
        )
        # Check that we were redirected to the home page anyway
        self.assertIn(
            'You probably want to <a href="/raclette/members/add"',
            resp.data.decode("utf-8"),
        )

    def test_password_reset_email_failure(self):
        self.create_project("raclette")
        for exception in (smtplib.SMTPException, socket.error):
            with patch.object(self.app.mail, "send", MagicMock(side_effect=exception)):
                resp = self.client.post(
                    "/password-reminder", data={"id": "raclette"}, follow_redirects=True
                )
            # Check that an error message is displayed
            self.assertIn(
                "there was an error while sending you an email",
                resp.data.decode("utf-8"),
            )
            # Check that we were not redirected to the success page
            self.assertNotIn(
                "A link to reset your password has been sent to you",
                resp.data.decode("utf-8"),
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
            self.assertIn(
                "there was an error while trying to send the invitation emails",
                resp.data.decode("utf-8"),
            )
            # Check that we are still on the same page (no redirection)
            self.assertIn(
                "Invite people to join this project", resp.data.decode("utf-8")
            )


class CaptchaTestCase(IhatemoneyTestCase):
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
            self.assertEqual(len(models.Project.query.all()), 1)

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
            self.assertEqual(len(models.Project.query.all()), 0)

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
            self.assertEqual(len(models.Project.query.all()), 0)

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
            self.assertEqual(len(models.Project.query.all()), 1)

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
        self.assertTrue(resp.status, 201)
        self.assertEqual(len(models.Project.query.all()), 1)


class TestCurrencyConverter(unittest.TestCase):
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
        self.assertEqual(one, two)

    def test_get_currencies(self):
        self.assertCountEqual(
            self.converter.get_currencies(),
            ["USD", "EUR", "CAD", "PLN", CurrencyConverter.no_currency],
        )

    def test_exchange_currency(self):
        result = self.converter.exchange_currency(100, "USD", "EUR")
        self.assertEqual(result, 80.0)

    def test_failing_remote(self):
        rates = {}
        with patch("requests.Response.json", new=lambda _: {}), self.assertWarns(
            UserWarning
        ):
            # we need a non-patched converter, but it seems that MagickMock
            # is mocking EVERY instance of the class method. Too bad.
            rates = CurrencyConverter.get_rates(self.converter)
        self.assertDictEqual(rates, {CurrencyConverter.no_currency: 1})


if __name__ == "__main__":
    unittest.main()
