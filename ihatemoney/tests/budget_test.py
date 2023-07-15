from collections import defaultdict
import datetime
import re
import unittest
from urllib.parse import urlparse, urlunparse

from flask import session, url_for
import pytest
from werkzeug.security import check_password_hash, generate_password_hash

from ihatemoney import models
from ihatemoney.currency_convertor import CurrencyConverter
from ihatemoney.tests.common.help_functions import extract_link
from ihatemoney.tests.common.ihatemoney_testcase import IhatemoneyTestCase
from ihatemoney.versioning import LoggingMode


class BudgetTestCase(IhatemoneyTestCase):
    def test_notifications(self):
        """Test that the notifications are sent, and that email addresses
        are checked properly.
        """
        # sending a message to one person
        with self.app.mail.record_messages() as outbox:
            # create a project
            self.login("raclette")

            self.post_project("raclette")
            resp = self.client.post(
                "/raclette/invite",
                data={"emails": "zorglub@notmyidea.org"},
                follow_redirects=True,
            )

            # success notification
            self.assertIn("Your invitations have been sent", resp.data.decode("utf-8"))

            self.assertEqual(len(outbox), 2)
            self.assertEqual(outbox[0].recipients, ["raclette@notmyidea.org"])
            self.assertEqual(outbox[1].recipients, ["zorglub@notmyidea.org"])

        # sending a message to multiple participants
        with self.app.mail.record_messages() as outbox:
            self.client.post(
                "/raclette/invite",
                data={"emails": "zorglub@notmyidea.org, toto@notmyidea.org"},
            )

            # only one message is sent to multiple participants
            self.assertEqual(len(outbox), 1)
            self.assertEqual(
                outbox[0].recipients, ["zorglub@notmyidea.org", "toto@notmyidea.org"]
            )

        # mail address checking
        with self.app.mail.record_messages() as outbox:
            response = self.client.post("/raclette/invite", data={"emails": "toto"})
            self.assertEqual(len(outbox), 0)  # no message sent
            self.assertIn(
                'The email <em class="font-italic">toto</em> is not valid',
                response.data.decode("utf-8"),
            )

        # mail address checking for escaping
        with self.app.mail.record_messages() as outbox:
            response = self.client.post(
                "/raclette/invite",
                data={"emails": "<img src=x onerror=alert(document.domain)>"},
            )
            self.assertEqual(len(outbox), 0)  # no message sent
            self.assertIn(
                'The email <em class="font-italic">'
                "&lt;img src=x onerror=alert(document.domain)&gt;"
                "</em> is not valid",
                response.data.decode("utf-8"),
            )

        # mixing good and wrong addresses shouldn't send any messages
        with self.app.mail.record_messages() as outbox:
            self.client.post(
                "/raclette/invite", data={"emails": "zorglub@notmyidea.org, zorglub"}
            )  # not valid

            # only one message is sent to multiple participants
            self.assertEqual(len(outbox), 0)

    def test_invite(self):
        """Test that invitation e-mails are sent properly"""
        self.login("raclette")
        self.post_project("raclette")
        with self.app.mail.record_messages() as outbox:
            self.client.post("/raclette/invite", data={"emails": "toto@notmyidea.org"})
            self.assertEqual(len(outbox), 1)
            url_start = outbox[0].body.find("You can log in using this link: ") + 32
            url_end = outbox[0].body.find(".\n", url_start)
            url = outbox[0].body[url_start:url_end]
        self.client.post("/exit")
        # Test that we got a valid token
        resp = self.client.get(url, follow_redirects=True)
        self.assertIn(
            'You probably want to <a href="/raclette/members/add"',
            resp.data.decode("utf-8"),
        )
        # Test empty and invalid tokens
        self.client.post("/exit")
        # Use another project_id
        parsed_url = urlparse(url)
        resp = self.client.get(
            urlunparse(
                parsed_url._replace(
                    path=parsed_url.path.replace("raclette/", "invalid_project/")
                )
            ),
            follow_redirects=True,
        )
        self.assertIn("Create a new project", resp.data.decode("utf-8"))

        # A token MUST have a point between payload and signature
        resp = self.client.get("/raclette/join/token.invalid", follow_redirects=True)
        self.assertIn("Provided token is invalid", resp.data.decode("utf-8"))

    def test_create_should_remember_project(self):
        """Test that creating a project adds it to the "logged in project" list,
        as it does for authentication
        """
        self.login("raclette")
        self.post_project("raclette")
        self.post_project("tartiflette")
        data = self.client.get("/raclette/").data.decode("utf-8")
        self.assertEqual(data.count('href="/tartiflette/"'), 1)

    def test_multiple_join(self):
        """Test that joining multiple times a project
        doesn't add it multiple times in the session"""
        self.login("raclette")
        self.post_project("raclette")
        project = self.get_project("raclette")
        invite_link = url_for(
            ".join_project", project_id="raclette", token=project.generate_token()
        )

        self.post_project("tartiflette")
        self.client.get(invite_link)
        data = self.client.get("/tartiflette/").data.decode("utf-8")
        # First join is OK
        self.assertIn('href="/raclette/"', data)

        # Second join shouldn't add a double link
        self.client.get(invite_link)
        data = self.client.get("/tartiflette/").data.decode("utf-8")
        self.assertEqual(data.count('href="/raclette/"'), 1)

    def test_invite_code_invalidation(self):
        """Test that invitation link expire after code change"""
        self.login("raclette")
        self.post_project("raclette")
        response = self.client.get("/raclette/invite").data.decode("utf-8")
        link = extract_link(response, "share the following link")

        self.client.post("/exit")
        response = self.client.get(link)
        # Link is valid
        self.assertEqual(response.status_code, 302)

        # Change password to invalidate token
        # Other data are required, but useless for the test
        response = self.client.post(
            "/raclette/edit",
            data={
                "name": "raclette",
                "contact_email": "zorglub@notmyidea.org",
                "password": "didoudida",
                "default_currency": "XXX",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("alert-danger", response.data.decode("utf-8"))

        self.client.post("/exit")
        response = self.client.get(link, follow_redirects=True)
        # Link is invalid
        self.assertIn("Provided token is invalid", response.data.decode("utf-8"))

    def test_password_reminder(self):
        # test that it is possible to have an email containing the password of a
        # project in case people forget it (and it happens!)

        self.create_project("raclette")

        with self.app.mail.record_messages() as outbox:
            # a nonexisting project should not send an email
            self.client.post("/password-reminder", data={"id": "unexisting"})
            self.assertEqual(len(outbox), 0)

            # a mail should be sent when a project exists
            self.client.post("/password-reminder", data={"id": "raclette"})
            self.assertEqual(len(outbox), 1)
            self.assertIn("raclette", outbox[0].body)
            self.assertIn("raclette@notmyidea.org", outbox[0].recipients)

    def test_password_reset(self):
        # test that a password can be changed using a link sent by mail

        self.create_project("raclette")
        # Get password resetting link from mail
        with self.app.mail.record_messages() as outbox:
            resp = self.client.post(
                "/password-reminder", data={"id": "raclette"}, follow_redirects=True
            )
            # Check that we are redirected to the right page
            self.assertIn(
                "A link to reset your password has been sent to you",
                resp.data.decode("utf-8"),
            )
            # Check that an email was sent
            self.assertEqual(len(outbox), 1)
            url_start = outbox[0].body.find("You can reset it here: ") + 23
            url_end = outbox[0].body.find(".\n", url_start)
            url = outbox[0].body[url_start:url_end]
        # Test that we got a valid token
        resp = self.client.get(url)
        self.assertIn("Password confirmation</label>", resp.data.decode("utf-8"))
        # Test that password can be changed
        self.client.post(
            url, data={"password": "pass", "password_confirmation": "pass"}
        )
        resp = self.login("raclette", password="pass")
        self.assertIn(
            "<title>Account manager - raclette</title>", resp.data.decode("utf-8")
        )
        # Test empty and null tokens
        resp = self.client.get("/reset-password")
        self.assertIn("No token provided", resp.data.decode("utf-8"))
        resp = self.client.get("/reset-password?token=token")
        self.assertIn("Invalid token", resp.data.decode("utf-8"))

    def test_project_creation(self):
        with self.client as c:
            with self.app.mail.record_messages() as outbox:
                # add a valid project
                resp = c.post(
                    "/create",
                    data={
                        "name": "The fabulous raclette party",
                        "id": "raclette",
                        "password": "party",
                        "contact_email": "raclette@notmyidea.org",
                        "default_currency": "USD",
                    },
                    follow_redirects=True,
                )

                # An email is sent to the owner with a reminder of the password.
                self.assertEqual(len(outbox), 1)
                self.assertEqual(outbox[0].recipients, ["raclette@notmyidea.org"])
                self.assertIn(
                    "A reminder email has just been sent to you",
                    resp.data.decode("utf-8"),
                )

            # session is updated
            self.assertTrue(session["raclette"])

            # project is created
            self.assertEqual(len(models.Project.query.all()), 1)

            # Add a second project with the same id
            self.get_project("raclette")

            c.post(
                "/create",
                data={
                    "name": "Another raclette party",
                    "id": "raclette",  # already used !
                    "password": "party",
                    "contact_email": "raclette@notmyidea.org",
                    "default_currency": "USD",
                },
            )

            # no new project added
            self.assertEqual(len(models.Project.query.all()), 1)

    def test_project_creation_without_public_permissions(self):
        self.app.config["ALLOW_PUBLIC_PROJECT_CREATION"] = False
        with self.client as c:
            # add a valid project
            c.post(
                "/create",
                data={
                    "name": "The fabulous raclette party",
                    "id": "raclette",
                    "password": "party",
                    "contact_email": "raclette@notmyidea.org",
                    "default_currency": "USD",
                },
            )

            # session is not updated
            self.assertNotIn("raclette", session)

            # project is not created
            self.assertEqual(len(models.Project.query.all()), 0)

    def test_project_creation_with_public_permissions(self):
        self.app.config["ALLOW_PUBLIC_PROJECT_CREATION"] = True
        with self.client as c:
            # add a valid project
            c.post(
                "/create",
                data={
                    "name": "The fabulous raclette party",
                    "id": "raclette",
                    "password": "party",
                    "contact_email": "raclette@notmyidea.org",
                    "default_currency": "USD",
                },
            )

            # session is updated
            self.assertTrue(session["raclette"])

            # project is created
            self.assertEqual(len(models.Project.query.all()), 1)

    def test_project_deletion(self):
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

            # project added
            self.assertEqual(len(models.Project.query.all()), 1)

            # Check that we can't delete project with a GET or with a
            # password-less POST.
            resp = self.client.get("/raclette/delete")
            self.assertEqual(resp.status_code, 405)
            self.client.post("/raclette/delete")
            self.assertEqual(len(models.Project.query.all()), 1)

            # Delete for real
            c.post(
                "/raclette/delete",
                data={"password": "party"},
            )

            # project removed
            self.assertEqual(len(models.Project.query.all()), 0)

    def test_bill_placeholder(self):
        self.post_project("raclette")
        self.login("raclette")

        result = self.client.get("/raclette/")

        # Empty bill list and no participant, should now propose to add participants first
        self.assertIn(
            'You probably want to <a href="/raclette/members/add"',
            result.data.decode("utf-8"),
        )

        result = self.client.post("/raclette/members/add", data={"name": "zorglub"})

        result = self.client.get("/raclette/")

        # Empty bill with member, list should now propose to add bills
        self.assertIn(
            'You probably want to <a href="/raclette/add"', result.data.decode("utf-8")
        )

    def test_membership(self):
        self.post_project("raclette")
        self.login("raclette")

        # adds a member to this project
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.assertEqual(len(self.get_project("raclette").members), 1)

        # adds him twice
        result = self.client.post("/raclette/members/add", data={"name": "zorglub"})

        # should not accept him
        self.assertEqual(len(self.get_project("raclette").members), 1)

        # add fred
        self.client.post("/raclette/members/add", data={"name": "fred"})
        self.assertEqual(len(self.get_project("raclette").members), 2)

        # check fred is present in the bills page
        result = self.client.get("/raclette/")
        self.assertIn("fred", result.data.decode("utf-8"))

        # remove fred
        self.client.post(
            "/raclette/members/%s/delete" % self.get_project("raclette").members[-1].id
        )

        # as fred is not bound to any bill, he is removed
        self.assertEqual(len(self.get_project("raclette").members), 1)

        # add fred again
        self.client.post("/raclette/members/add", data={"name": "fred"})
        fred_id = self.get_project("raclette").members[-1].id

        # bound him to a bill
        result = self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": fred_id,
                "payed_for": [fred_id],
                "amount": "25",
            },
        )

        # remove fred
        self.client.post(f"/raclette/members/{fred_id}/delete")

        # he is still in the database, but is deactivated
        self.assertEqual(len(self.get_project("raclette").members), 2)
        self.assertEqual(len(self.get_project("raclette").active_members), 1)

        # as fred is now deactivated, check that he is not listed when adding
        # a bill or displaying the balance
        result = self.client.get("/raclette/")
        self.assertNotIn(
            (f"/raclette/members/{fred_id}/delete"), result.data.decode("utf-8")
        )

        result = self.client.get("/raclette/add")
        self.assertNotIn("fred", result.data.decode("utf-8"))

        # adding him again should reactivate him
        self.client.post("/raclette/members/add", data={"name": "fred"})
        self.assertEqual(len(self.get_project("raclette").active_members), 2)

        # adding an user with the same name as another user from a different
        # project should not cause any troubles
        self.post_project("randomid")
        self.login("randomid")
        self.client.post("/randomid/members/add", data={"name": "fred"})
        self.assertEqual(len(self.get_project("randomid").active_members), 1)

    def test_person_model(self):
        self.post_project("raclette")
        self.login("raclette")

        # adds a member to this project
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        zorglub = self.get_project("raclette").members[-1]

        # should not have any bills
        self.assertFalse(zorglub.has_bills())

        # bound him to a bill
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": zorglub.id,
                "payed_for": [zorglub.id],
                "amount": "25",
            },
        )

        # should have a bill now
        zorglub = self.get_project("raclette").members[-1]
        self.assertTrue(zorglub.has_bills())

    def test_member_delete_method(self):
        self.post_project("raclette")
        self.login("raclette")

        # adds a member to this project
        self.client.post("/raclette/members/add", data={"name": "zorglub"})

        # try to remove the member using GET method
        response = self.client.get("/raclette/members/1/delete")
        self.assertEqual(response.status_code, 405)

        # delete user using POST method
        self.client.post("/raclette/members/1/delete")
        self.assertEqual(len(self.get_project("raclette").active_members), 0)
        # try to delete an user already deleted
        self.client.post("/raclette/members/1/delete")

    def test_demo(self):
        # test that a demo project is created if none is defined
        self.assertEqual([], models.Project.query.all())
        self.client.get("/demo")
        demo = self.get_project("demo")
        self.assertTrue(demo is not None)

        self.assertEqual(["Amina", "Georg", "Alice"], [m.name for m in demo.members])
        self.assertEqual(demo.get_bills().count(), 3)

    def test_deactivated_demo(self):
        self.app.config["ACTIVATE_DEMO_PROJECT"] = False

        # test redirection to the create project form when demo is deactivated
        resp = self.client.get("/demo")
        self.assertIn('<a href="/create?project_id=demo">', resp.data.decode("utf-8"))

    def test_authentication(self):
        # try to authenticate without credentials should redirect
        # to the authentication page
        resp = self.client.post("/authenticate")
        self.assertIn("Authentication", resp.data.decode("utf-8"))

        # raclette that the login / logout process works
        self.create_project("raclette")

        # try to see the project while not being authenticated should redirect
        # to the authentication page
        resp = self.client.get("/raclette", follow_redirects=True)
        self.assertIn("Authentication", resp.data.decode("utf-8"))

        # try to connect with wrong credentials should not work
        with self.client as c:
            resp = c.post("/authenticate", data={"id": "raclette", "password": "nope"})

            self.assertIn("Authentication", resp.data.decode("utf-8"))
            self.assertNotIn("raclette", session)

        # try to connect with the right credentials should work
        with self.client as c:
            resp = c.post(
                "/authenticate", data={"id": "raclette", "password": "raclette"}
            )

            self.assertNotIn("Authentication", resp.data.decode("utf-8"))
            self.assertIn("raclette", session)
            self.assertTrue(session["raclette"])

            # logout should work with POST only
            resp = c.get("/exit")
            self.assertStatus(405, resp)

            # logout should wipe the session out
            c.post("/exit")
            self.assertNotIn("raclette", session)

        # test that with admin credentials, one can access every project
        self.app.config["ADMIN_PASSWORD"] = generate_password_hash("pass")
        with self.client as c:
            resp = c.post("/admin?goto=%2Fraclette", data={"admin_password": "pass"})
            self.assertNotIn("Authentication", resp.data.decode("utf-8"))
            self.assertTrue(session["is_admin"])

    def test_authentication_with_upper_case(self):
        self.post_project("Raclette")

        # try to connect with the right credentials should work
        with self.client as c:
            resp = c.post(
                "/authenticate", data={"id": "Raclette", "password": "Raclette"}
            )

            self.assertNotIn("Authentication", resp.data.decode("utf-8"))
            self.assertIn("raclette", session)
            self.assertTrue(session["raclette"])

    def test_admin_authentication(self):
        self.app.config["ADMIN_PASSWORD"] = generate_password_hash("pass")
        # Disable public project creation so we have an admin endpoint to test
        self.app.config["ALLOW_PUBLIC_PROJECT_CREATION"] = False

        # test the redirection to the authentication page when trying to access admin endpoints
        resp = self.client.get("/create")
        self.assertIn('<a href="/admin?goto=%2Fcreate">', resp.data.decode("utf-8"))

        # test right password
        resp = self.client.post(
            "/admin?goto=%2Fcreate", data={"admin_password": "pass"}
        )
        self.assertIn('<a href="/create">/create</a>', resp.data.decode("utf-8"))

        # test wrong password
        resp = self.client.post(
            "/admin?goto=%2Fcreate", data={"admin_password": "wrong"}
        )
        self.assertNotIn('<a href="/create">/create</a>', resp.data.decode("utf-8"))

        # test empty password
        resp = self.client.post("/admin?goto=%2Fcreate", data={"admin_password": ""})
        self.assertNotIn('<a href="/create">/create</a>', resp.data.decode("utf-8"))

    def test_login_throttler(self):
        self.app.config["ADMIN_PASSWORD"] = generate_password_hash("pass")

        # Activate admin login throttling by authenticating 4 times with a wrong passsword
        self.client.post("/admin?goto=%2Fcreate", data={"admin_password": "wrong"})
        self.client.post("/admin?goto=%2Fcreate", data={"admin_password": "wrong"})
        self.client.post("/admin?goto=%2Fcreate", data={"admin_password": "wrong"})
        resp = self.client.post(
            "/admin?goto=%2Fcreate", data={"admin_password": "wrong"}
        )

        self.assertIn(
            "Too many failed login attempts.",
            resp.data.decode("utf-8"),
        )
        # Try with limiter disabled
        from ihatemoney.utils import limiter

        try:
            limiter.enabled = False
            resp = self.client.post(
                "/admin?goto=%2Fcreate", data={"admin_password": "wrong"}
            )
            self.assertNotIn(
                "Too many failed login attempts.",
                resp.data.decode("utf-8"),
            )
        finally:
            limiter.enabled = True

    def test_manage_bills(self):
        self.post_project("raclette")

        # add two participants
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "fred"})

        members_ids = [m.id for m in self.get_project("raclette").members]

        # create a bill
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": members_ids[0],
                "payed_for": members_ids,
                "amount": "25",
            },
        )
        self.get_project("raclette")
        bill = models.Bill.query.one()
        self.assertEqual(bill.amount, 25)

        # edit the bill
        self.client.post(
            f"/raclette/edit/{bill.id}",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": members_ids[0],
                "payed_for": members_ids,
                "amount": "10",
            },
        )

        bill = models.Bill.query.one()
        self.assertEqual(bill.amount, 10, "bill edition")

        # Try to delete the bill with a GET: it should fail
        response = self.client.get(f"/raclette/delete/{bill.id}")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(1, len(models.Bill.query.all()), "bill deletion")
        # Really delete the bill
        self.client.post(f"/raclette/delete/{bill.id}")
        self.assertEqual(0, len(models.Bill.query.all()), "bill deletion")

        # test balance
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": members_ids[0],
                "payed_for": members_ids,
                "amount": "19",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": members_ids[1],
                "payed_for": members_ids[0],
                "amount": "20",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": members_ids[1],
                "payed_for": members_ids,
                "amount": "17",
            },
        )

        balance = self.get_project("raclette").balance
        self.assertEqual(set(balance.values()), set([19.0, -19.0]))

        # Bill with negative amount
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-12",
                "what": "fromage à raclette",
                "payer": members_ids[0],
                "payed_for": members_ids,
                "amount": "-25",
            },
        )
        bill = models.Bill.query.filter(models.Bill.date == "2011-08-12")[0]
        self.assertEqual(bill.amount, -25)

        # add a bill with a comma
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-01",
                "what": "fromage à raclette",
                "payer": members_ids[0],
                "payed_for": members_ids,
                "amount": "25,02",
            },
        )
        bill = models.Bill.query.filter(models.Bill.date == "2011-08-01")[0]
        self.assertEqual(bill.amount, 25.02)

        # add a bill with a valid external link
        self.client.post(
            "/raclette/add",
            data={
                "date": "2015-05-05",
                "what": "fromage à raclette",
                "payer": members_ids[0],
                "payed_for": members_ids,
                "amount": "42",
                "external_link": "https://example.com/fromage",
            },
        )
        bill = models.Bill.query.filter(models.Bill.date == "2015-05-05")[0]
        self.assertEqual(bill.external_link, "https://example.com/fromage")

        # add a bill with an invalid external link
        resp = self.client.post(
            "/raclette/add",
            data={
                "date": "2015-05-06",
                "what": "mauvais fromage à raclette",
                "payer": members_ids[0],
                "payed_for": members_ids,
                "amount": "42000",
                "external_link": "javascript:alert('Tu bluffes, Martoni.')",
            },
        )
        self.assertIn("Invalid URL", resp.data.decode("utf-8"))

    def test_weighted_balance(self):
        self.post_project("raclette")

        # add two participants
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post(
            "/raclette/members/add", data={"name": "freddy familly", "weight": 4}
        )

        members_ids = [m.id for m in self.get_project("raclette").members]

        # test balance
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": members_ids[0],
                "payed_for": members_ids,
                "amount": "10",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "pommes de terre",
                "payer": members_ids[1],
                "payed_for": members_ids,
                "amount": "10",
            },
        )

        balance = self.get_project("raclette").balance
        self.assertEqual(set(balance.values()), set([6, -6]))

    def test_trimmed_members(self):
        self.post_project("raclette")

        # Add two times the same person (with a space at the end).
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "zorglub "})
        members = self.get_project("raclette").members

        self.assertEqual(len(members), 1)

    def test_weighted_members_list(self):
        self.post_project("raclette")

        # add two participants
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "tata", "weight": 1})

        resp = self.client.get("/raclette/")
        self.assertIn("extra-info", resp.data.decode("utf-8"))

        self.client.post(
            "/raclette/members/add", data={"name": "freddy familly", "weight": 4}
        )

        resp = self.client.get("/raclette/")
        self.assertNotIn("extra-info", resp.data.decode("utf-8"))

    def test_negative_weight(self):
        self.post_project("raclette")

        # Add one user and edit it to have a negative share
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        resp = self.client.post(
            "/raclette/members/1/edit", data={"name": "zorglub", "weight": -1}
        )

        # An error should be generated, and its weight should still be 1.
        self.assertIn('<p class="alert alert-danger">', resp.data.decode("utf-8"))
        self.assertEqual(len(self.get_project("raclette").members), 1)
        self.assertEqual(self.get_project("raclette").members[0].weight, 1)

    def test_rounding(self):
        self.post_project("raclette")

        # add participants
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "fred"})
        self.client.post("/raclette/members/add", data={"name": "tata"})

        # create bills
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1, 2, 3],
                "amount": "24.36",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "red wine",
                "payer": 2,
                "payed_for": [1],
                "amount": "19.12",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "delicatessen",
                "payer": 1,
                "payed_for": [1, 2],
                "amount": "22",
            },
        )

        balance = self.get_project("raclette").balance
        result = {}
        result[self.get_project("raclette").members[0].id] = 8.12
        result[self.get_project("raclette").members[1].id] = 0.0
        result[self.get_project("raclette").members[2].id] = -8.12
        # Since we're using floating point to store currency, we can have some
        # rounding issues that prevent test from working.
        # However, we should obtain the same values as the theoretical ones if we
        # round to 2 decimals, like in the UI.
        for key, value in balance.items():
            self.assertEqual(round(value, 2), result[key])

    def test_edit_project(self):
        # A project should be editable

        self.post_project("raclette")
        new_data = {
            "name": "Super raclette party!",
            "contact_email": "zorglub@notmyidea.org",
            "password": "didoudida",
            "logging_preference": LoggingMode.ENABLED.value,
            "default_currency": "USD",
        }

        resp = self.client.post("/raclette/edit", data=new_data, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        project = self.get_project("raclette")

        self.assertEqual(project.name, new_data["name"])
        self.assertEqual(project.contact_email, new_data["contact_email"])
        self.assertEqual(project.default_currency, new_data["default_currency"])
        self.assertTrue(check_password_hash(project.password, new_data["password"]))

        # Editing a project with a wrong email address should fail
        new_data["contact_email"] = "wrong_email"

        resp = self.client.post("/raclette/edit", data=new_data, follow_redirects=True)
        self.assertIn("Invalid email address", resp.data.decode("utf-8"))

    def test_dashboard(self):
        # test that the dashboard is deactivated by default
        resp = self.client.post(
            "/admin?goto=%2Fdashboard",
            data={"admin_password": "adminpass"},
            follow_redirects=True,
        )
        self.assertIn('<div class="alert alert-danger">', resp.data.decode("utf-8"))

        # test access to the dashboard when it is activated
        self.enable_admin()
        resp = self.client.get("/dashboard")
        self.assertIn(
            """<thead>
        <tr>
            <th>Project</th>
            <th>Number of participants</th>""",
            resp.data.decode("utf-8"),
        )

    def test_dashboard_project_deletion(self):
        self.post_project("raclette")
        self.enable_admin()
        resp = self.client.get("/dashboard")
        pattern = re.compile(r"<form id=\"delete-project\" [^>]*?action=\"(.*?)\"")
        match = pattern.search(resp.data.decode("utf-8"))
        self.assertIsNotNone(match)
        self.assertIsNotNone(match.group(1))

        resp = self.client.post(match.group(1))

        # project removed
        self.assertEqual(len(models.Project.query.all()), 0)

    def test_statistics_page(self):
        self.post_project("raclette")
        response = self.client.get("/raclette/statistics")
        self.assertEqual(response.status_code, 200)

    def test_statistics(self):
        # Output is checked with the USD sign
        self.post_project("raclette", default_currency="USD")

        # add participants
        self.client.post("/raclette/members/add", data={"name": "zorglub", "weight": 2})
        self.client.post("/raclette/members/add", data={"name": "fred"})
        self.client.post("/raclette/members/add", data={"name": "tata"})
        # Add a participant with a balance at 0 :
        self.client.post("/raclette/members/add", data={"name": "pépé"})

        # Check that there are no monthly statistics and no active months
        project = self.get_project("raclette")
        self.assertEqual(len(project.active_months_range()), 0)
        self.assertEqual(len(project.monthly_stats), 0)

        # Check that the "monthly expenses" table is empty
        response = self.client.get("/raclette/statistics")
        regex = (
            r"<table id=\"monthly_stats\".*>\s*<thead>\s*<tr>\s*<th>Period</th>\s*"
            r"<th>Spent</th>\s*</tr>\s*</thead>\s*<tbody>\s*</tbody>\s*</table>"
        )
        self.assertRegex(response.data.decode("utf-8"), regex)

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

        response = self.client.get("/raclette/statistics")
        regex = r"<td class=\"d-md-none\">{}</td>\s*<td>{}</td>\s*<td>{}</td>"
        self.assertRegex(
            response.data.decode("utf-8"),
            regex.format("zorglub", r"\$20\.00", r"\$31\.67"),
        )
        self.assertRegex(
            response.data.decode("utf-8"),
            regex.format("fred", r"\$20\.00", r"\$5\.83"),
        )
        self.assertRegex(
            response.data.decode("utf-8"), regex.format("tata", r"\$0\.00", r"\$2\.50")
        )
        self.assertRegex(
            response.data.decode("utf-8"), regex.format("pépé", r"\$0\.00", r"\$0\.00")
        )

        # Check that the order of participants in the sidebar table is the
        # same as in the main table.
        order = ["fred", "pépé", "tata", "zorglub"]
        regex1 = r".*".join(
            r"<td class=\"balance-name\">{}</td>".format(name) for name in order
        )
        regex2 = r".*".join(
            r"<td class=\"d-md-none\">{}</td>".format(name) for name in order
        )
        # Build the regexp ourselves to be able to pass the DOTALL flag
        # (so that ".*" matches newlines)
        self.assertRegex(response.data.decode("utf-8"), re.compile(regex1, re.DOTALL))
        self.assertRegex(response.data.decode("utf-8"), re.compile(regex2, re.DOTALL))

        # Check monthly expenses again: it should have a single month and the correct amount
        august = datetime.date(year=2011, month=8, day=1)
        self.assertEqual(project.active_months_range(), [august])
        self.assertEqual(dict(project.monthly_stats[2011]), {8: 40.0})

        # Add bills for other months and check monthly expenses again
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-12-20",
                "what": "fromage à raclette",
                "payer": 2,
                "payed_for": [1, 2],
                "amount": "30",
            },
        )
        months = [
            datetime.date(year=2011, month=12, day=1),
            datetime.date(year=2011, month=11, day=1),
            datetime.date(year=2011, month=10, day=1),
            datetime.date(year=2011, month=9, day=1),
            datetime.date(year=2011, month=8, day=1),
        ]
        amounts_2011 = {
            12: 30.0,
            8: 40.0,
        }
        self.assertEqual(project.active_months_range(), months)
        self.assertEqual(dict(project.monthly_stats[2011]), amounts_2011)

        # Test more corner cases: first day of month as oldest bill
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-01",
                "what": "ice cream",
                "payer": 2,
                "payed_for": [1, 2],
                "amount": "10",
            },
        )
        amounts_2011[8] += 10.0
        self.assertEqual(project.active_months_range(), months)
        self.assertEqual(dict(project.monthly_stats[2011]), amounts_2011)

        # Last day of month as newest bill
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-12-31",
                "what": "champomy",
                "payer": 1,
                "payed_for": [1, 2],
                "amount": "10",
            },
        )
        amounts_2011[12] += 10.0
        self.assertEqual(project.active_months_range(), months)
        self.assertEqual(dict(project.monthly_stats[2011]), amounts_2011)

        # Last day of month as oldest bill
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-07-31",
                "what": "smoothie",
                "payer": 1,
                "payed_for": [1, 2],
                "amount": "20",
            },
        )
        months.append(datetime.date(year=2011, month=7, day=1))
        amounts_2011[7] = 20.0
        self.assertEqual(project.active_months_range(), months)
        self.assertEqual(dict(project.monthly_stats[2011]), amounts_2011)

        # First day of month as newest bill
        self.client.post(
            "/raclette/add",
            data={
                "date": "2012-01-01",
                "what": "more champomy",
                "payer": 2,
                "payed_for": [1, 2],
                "amount": "30",
            },
        )
        months.insert(0, datetime.date(year=2012, month=1, day=1))
        amounts_2012 = {1: 30.0}
        self.assertEqual(project.active_months_range(), months)
        self.assertEqual(dict(project.monthly_stats[2011]), amounts_2011)
        self.assertEqual(dict(project.monthly_stats[2012]), amounts_2012)

    def test_settle_page(self):
        self.post_project("raclette")
        response = self.client.get("/raclette/settle_bills")
        self.assertEqual(response.status_code, 200)

    def test_settle(self):
        self.post_project("raclette")

        # add participants
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "fred"})
        self.client.post("/raclette/members/add", data={"name": "tata"})
        # Add a participant with a balance at 0 :
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
        project = self.get_project("raclette")
        transactions = project.get_transactions_to_settle_bill()
        members = defaultdict(int)
        # We should have the same values between transactions and project balances
        for t in transactions:
            members[t["ower"]] -= t["amount"]
            members[t["receiver"]] += t["amount"]
        balance = self.get_project("raclette").balance
        for m, a in members.items():
            self.assertAlmostEqual(a, balance[m.id], delta=0.01)
        return

    def test_settle_zero(self):
        self.post_project("raclette")

        # add participants
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "fred"})
        self.client.post("/raclette/members/add", data={"name": "tata"})

        # create bills
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1, 2, 3],
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
                "amount": "20",
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
        project = self.get_project("raclette")
        transactions = project.get_transactions_to_settle_bill()

        # There should not be any zero-amount transfer after rounding
        for t in transactions:
            rounded_amount = round(t["amount"], 2)
            self.assertNotEqual(
                0.0,
                rounded_amount,
                msg=f"{t['amount']} is equal to zero after rounding",
            )

    def test_access_other_projects(self):
        """Test that accessing or editing bills and participants from another project fails"""
        # Create project
        self.post_project("raclette")

        # Add participants
        self.client.post("/raclette/members/add", data={"name": "zorglub", "weight": 2})
        self.client.post("/raclette/members/add", data={"name": "fred"})
        self.client.post("/raclette/members/add", data={"name": "tata"})
        self.client.post("/raclette/members/add", data={"name": "pépé"})

        # Create bill
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
        # Ensure it has been created
        raclette = self.get_project("raclette")
        self.assertEqual(raclette.get_bills().count(), 1)

        # Log out
        self.client.post("/exit")

        # Create and log in as another project
        self.post_project("tartiflette")

        modified_bill = {
            "date": "2018-12-31",
            "what": "roblochon",
            "payer": 2,
            "payed_for": [1, 3, 4],
            "amount": "100.0",
        }
        # Try to access bill of another project
        resp = self.client.get("/raclette/edit/1")
        self.assertStatus(303, resp)
        # Try to access bill of another project by ID
        resp = self.client.get("/tartiflette/edit/1")
        self.assertStatus(404, resp)
        # Try to edit bill
        resp = self.client.post("/raclette/edit/1", data=modified_bill)
        self.assertStatus(303, resp)
        # Try to edit bill by ID
        resp = self.client.post("/tartiflette/edit/1", data=modified_bill)
        self.assertStatus(404, resp)
        # Try to delete bill
        resp = self.client.post("/raclette/delete/1")
        self.assertStatus(303, resp)
        # Try to delete bill by ID
        resp = self.client.post("/tartiflette/delete/1")
        self.assertStatus(302, resp)

        # Additional check that the bill was indeed not modified or deleted
        bill = models.Bill.query.filter(models.Bill.id == 1).one()
        self.assertEqual(bill.what, "fromage à raclette")

        # Use the correct credentials to modify and delete the bill.
        # This ensures that modifying and deleting the bill can actually work

        self.client.post("/exit")
        self.client.post(
            "/authenticate", data={"id": "raclette", "password": "raclette"}
        )
        self.client.post("/raclette/edit/1", data=modified_bill)
        bill = models.Bill.query.filter(models.Bill.id == 1).one_or_none()
        self.assertNotEqual(bill, None, "bill not found")
        self.assertEqual(bill.what, "roblochon")
        self.client.post("/raclette/delete/1")
        bill = models.Bill.query.filter(models.Bill.id == 1).one_or_none()
        self.assertEqual(bill, None)

        # Switch back to the second project
        self.client.post("/exit")
        self.client.post(
            "/authenticate", data={"id": "tartiflette", "password": "tartiflette"}
        )
        modified_member = {
            "name": "bulgroz",
            "weight": 42,
        }
        # Try to access member from another project
        resp = self.client.get("/raclette/members/1/edit")
        self.assertStatus(303, resp)
        # Try to access member by ID
        resp = self.client.get("/tartiflette/members/1/edit")
        self.assertStatus(404, resp)
        # Try to edit member
        resp = self.client.post("/raclette/members/1/edit", data=modified_member)
        self.assertStatus(303, resp)
        # Try to edit member by ID
        resp = self.client.post("/tartiflette/members/1/edit", data=modified_member)
        self.assertStatus(404, resp)
        # Try to delete member
        resp = self.client.post("/raclette/members/1/delete")
        self.assertStatus(303, resp)
        # Try to delete member by ID
        resp = self.client.post("/tartiflette/members/1/delete")
        self.assertStatus(302, resp)

        # Additional check that the member was indeed not modified or deleted
        member = models.Person.query.filter(models.Person.id == 1).one_or_none()
        self.assertNotEqual(member, None, "member not found")
        self.assertEqual(member.name, "zorglub")
        self.assertTrue(member.activated)

        # Use the correct credentials to modify and delete the member.
        # This ensures that modifying and deleting the member can actually work
        self.client.post("/exit")
        self.client.post(
            "/authenticate", data={"id": "raclette", "password": "raclette"}
        )
        self.client.post("/raclette/members/1/edit", data=modified_member)
        member = models.Person.query.filter(models.Person.id == 1).one()
        self.assertEqual(member.name, "bulgroz")
        self.client.post("/raclette/members/1/delete")
        member = models.Person.query.filter(models.Person.id == 1).one_or_none()
        self.assertEqual(member, None)

    def test_currency_switch(self):
        # A project should be editable
        self.post_project("raclette")

        # add participants
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "fred"})
        self.client.post("/raclette/members/add", data={"name": "tata"})

        # create bills
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1, 2, 3],
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
                "amount": "20",
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

        project = self.get_project("raclette")

        # First all converted_amount should be the same as amount, with no currency
        for bill in project.get_bills():
            self.assertEqual(bill.original_currency, CurrencyConverter.no_currency)
            self.assertEqual(bill.amount, bill.converted_amount)

        # Then, switch to EUR, all bills must have been changed to this currency
        project.switch_currency("EUR")
        for bill in project.get_bills():
            self.assertEqual(bill.original_currency, "EUR")
            self.assertEqual(bill.amount, bill.converted_amount)

        # Add a bill in EUR, the current default currency
        self.client.post(
            "/raclette/add",
            data={
                "date": "2017-01-01",
                "what": "refund from EUR",
                "payer": 3,
                "payed_for": [2],
                "amount": "20",
                "original_currency": "EUR",
            },
        )
        last_bill = project.get_bills().first()
        self.assertEqual(last_bill.converted_amount, last_bill.amount)

        # Erase all currencies
        project.switch_currency(CurrencyConverter.no_currency)
        for bill in project.get_bills():
            self.assertEqual(bill.original_currency, CurrencyConverter.no_currency)
            self.assertEqual(bill.amount, bill.converted_amount)

        # Let's go back to EUR to test conversion
        project.switch_currency("EUR")
        # This is a bill in CAD
        self.client.post(
            "/raclette/add",
            data={
                "date": "2017-01-01",
                "what": "Poutine",
                "payer": 3,
                "payed_for": [2],
                "amount": "18",
                "original_currency": "CAD",
            },
        )
        last_bill = project.get_bills().first()
        expected_amount = self.converter.exchange_currency(
            last_bill.amount, "CAD", "EUR"
        )
        self.assertEqual(last_bill.converted_amount, expected_amount)

        # Switch to USD. Now, NO bill should be in USD, since they already had a currency
        project.switch_currency("USD")
        for bill in project.get_bills():
            self.assertNotEqual(bill.original_currency, "USD")
            expected_amount = self.converter.exchange_currency(
                bill.amount, bill.original_currency, "USD"
            )
            self.assertEqual(bill.converted_amount, expected_amount)

        # Switching back to no currency must fail
        with pytest.raises(ValueError):
            project.switch_currency(CurrencyConverter.no_currency)

        # It also must fails with a nice error using the form
        resp = self.client.post(
            "/raclette/edit",
            data={
                "name": "demonstration",
                "password": "demo",
                "contact_email": "demo@notmyidea.org",
                "project_history": "y",
                "default_currency": CurrencyConverter.no_currency,
            },
        )
        # A user displayed error should be generated, and its currency should be the same.
        self.assertStatus(200, resp)
        self.assertIn('<p class="alert alert-danger">', resp.data.decode("utf-8"))
        self.assertEqual(self.get_project("raclette").default_currency, "USD")

    def test_currency_switch_to_bill_currency(self):
        # Default currency is 'XXX', but we should start from a project with a currency
        self.post_project("raclette", default_currency="USD")

        # add participants
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "fred"})

        # Bill with a different currency than project's default
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1, 2],
                "amount": "10.0",
                "original_currency": "EUR",
            },
        )

        project = self.get_project("raclette")

        bill = project.get_bills().first()
        self.assertEqual(
            self.converter.exchange_currency(bill.amount, "EUR", "USD"),
            bill.converted_amount,
        )

        # And switch project to the currency from the bill we created
        project.switch_currency("EUR")
        bill = project.get_bills().first()
        self.assertEqual(bill.converted_amount, bill.amount)

    def test_currency_switch_to_no_currency(self):
        # Default currency is 'XXX', but we should start from a project with a currency
        self.post_project("raclette", default_currency="USD")

        # add participants
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "fred"})

        # Bills with a different currency than project's default
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1, 2],
                "amount": "10.0",
                "original_currency": "EUR",
            },
        )

        self.client.post(
            "/raclette/add",
            data={
                "date": "2017-01-01",
                "what": "aspirine",
                "payer": 2,
                "payed_for": [1, 2],
                "amount": "5.0",
                "original_currency": "EUR",
            },
        )

        project = self.get_project("raclette")

        for bill in project.get_bills_unordered():
            self.assertEqual(
                self.converter.exchange_currency(bill.amount, "EUR", "USD"),
                bill.converted_amount,
            )

        # And switch project to no currency: amount should be equal to what was submitted
        project.switch_currency(CurrencyConverter.no_currency)
        no_currency_bills = [
            (bill.amount, bill.converted_amount) for bill in project.get_bills()
        ]
        self.assertEqual(no_currency_bills, [(5.0, 5.0), (10.0, 10.0)])

    def test_amount_is_null(self):
        self.post_project("raclette")

        # add participants
        self.client.post("/raclette/members/add", data={"name": "zorglub"})

        # null amount
        self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1],
                "amount": "0",
                "original_currency": "EUR",
            },
        )

        # Bill should have been accepted
        project = self.get_project("raclette")
        self.assertEqual(project.get_bills().count(), 1)
        last_bill = project.get_bills().first()
        self.assertEqual(last_bill.amount, 0)

    def test_decimals_on_weighted_members_list(self):
        self.post_project("raclette")

        # add three users with different weights
        self.client.post(
            "/raclette/members/add", data={"name": "zorglub", "weight": 1.0}
        )
        self.client.post("/raclette/members/add", data={"name": "tata", "weight": 1.10})
        self.client.post("/raclette/members/add", data={"name": "fred", "weight": 1.15})

        # check if weights of the users are 1, 1.1, 1.15 respectively
        resp = self.client.get("/raclette/")
        self.assertIn(
            'zorglub<span class="light">(x1)</span>', resp.data.decode("utf-8")
        )
        self.assertIn(
            'tata<span class="light">(x1.1)</span>', resp.data.decode("utf-8")
        )
        self.assertIn(
            'fred<span class="light">(x1.15)</span>', resp.data.decode("utf-8")
        )

    def test_amount_too_high(self):
        self.post_project("raclette")

        # add participants
        self.client.post("/raclette/members/add", data={"name": "zorglub"})

        # High amount should be rejected.
        # See https://github.com/python-babel/babel/issues/821
        resp = self.client.post(
            "/raclette/add",
            data={
                "date": "2016-12-31",
                "what": "fromage à raclette",
                "payer": 1,
                "payed_for": [1],
                "amount": "9347242149381274732472348728748723473278472843.12",
                "original_currency": "EUR",
            },
        )
        self.assertIn('<p class="alert alert-danger">', resp.data.decode("utf-8"))

        # Without any check, the following request will fail.
        resp = self.client.get("/raclette/")
        # No bills, the previous one was not added
        self.assertIn("No bills", resp.data.decode("utf-8"))

    def test_session_projects_migration_to_list(self):
        """In https://github.com/spiral-project/ihatemoney/pull/1082, session["projects"]
        was migrated from a list to a dict. We need to handle this.
        """
        self.post_project("raclette")
        self.client.get("/exit")

        with self.client as c:
            c.post("/authenticate", data={"id": "raclette", "password": "raclette"})
            self.assertTrue(session["raclette"])
            # New behavior
            self.assertIsInstance(session["projects"], dict)
            # Now, go back to the past
            with c.session_transaction() as sess:
                sess["projects"] = [("raclette", "raclette")]
            # It should convert entry to dict
            c.get("/")
            self.assertIsInstance(session["projects"], dict)
            self.assertIn("raclette", session["projects"])


if __name__ == "__main__":
    unittest.main()
