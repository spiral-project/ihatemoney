from collections import defaultdict
import datetime
import re
from urllib.parse import urlparse, urlunparse

from flask import session, url_for
from libfaketime import fake_time
import pytest
from werkzeug.security import check_password_hash

from ihatemoney import models
from ihatemoney.currency_convertor import CurrencyConverter
from ihatemoney.tests.common.help_functions import extract_link
from ihatemoney.tests.common.ihatemoney_testcase import IhatemoneyTestCase
from ihatemoney.utils import generate_password_hash
from ihatemoney.versioning import LoggingMode
from ihatemoney.web import build_etag


class TestBudget(IhatemoneyTestCase):
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
            assert "Your invitations have been sent" in resp.data.decode("utf-8")

            assert len(outbox) == 2
            assert outbox[0].recipients == ["raclette@notmyidea.org"]
            assert outbox[1].recipients == ["zorglub@notmyidea.org"]

        # sending a message to multiple participants
        with self.app.mail.record_messages() as outbox:
            self.client.post(
                "/raclette/invite",
                data={"emails": "zorglub@notmyidea.org, toto@notmyidea.org"},
            )

            # only one message is sent to multiple participants
            assert len(outbox) == 1
            assert outbox[0].recipients == [
                "zorglub@notmyidea.org",
                "toto@notmyidea.org",
            ]

        # mail address checking
        with self.app.mail.record_messages() as outbox:
            response = self.client.post("/raclette/invite", data={"emails": "toto"})
            assert len(outbox) == 0  # no message sent
            assert (
                'The email <em class="font-italic">toto</em> is not valid'
                in response.data.decode("utf-8")
            )

        # mail address checking for escaping
        with self.app.mail.record_messages() as outbox:
            response = self.client.post(
                "/raclette/invite",
                data={"emails": "<img src=x onerror=alert(document.domain)>"},
            )
            assert len(outbox) == 0  # no message sent
            assert (
                'The email <em class="font-italic">'
                "&lt;img src=x onerror=alert(document.domain)&gt;"
                "</em> is not valid" in response.data.decode("utf-8")
            )

        # mixing good and wrong addresses shouldn't send any messages
        with self.app.mail.record_messages() as outbox:
            self.client.post(
                "/raclette/invite", data={"emails": "zorglub@notmyidea.org, zorglub"}
            )  # not valid

            # only one message is sent to multiple participants
            assert len(outbox) == 0

    def test_invite(self):
        """Test that invitation e-mails are sent properly"""
        self.login("raclette")
        self.post_project("raclette")
        with self.app.mail.record_messages() as outbox:
            self.client.post("/raclette/invite", data={"emails": "toto@notmyidea.org"})
            assert len(outbox) == 1
            url_start = outbox[0].body.find("You can log in using this link: ") + 32
            url_end = outbox[0].body.find(".\n", url_start)
            url = outbox[0].body[url_start:url_end]
        self.client.post("/exit")
        # Test that we got a valid token
        resp = self.client.get(url, follow_redirects=True)
        assert (
            '<a href="/raclette/members/add">Add the first participant'
            in resp.data.decode("utf-8")
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
        assert "Create a new project" in resp.data.decode("utf-8")

        # A token MUST have a point between payload and signature
        resp = self.client.get("/raclette/join/token.invalid", follow_redirects=True)
        assert "Provided token is invalid" in resp.data.decode("utf-8")

    def test_create_should_remember_project(self):
        """Test that creating a project adds it to the "logged in project" list,
        as it does for authentication
        """
        self.login("raclette")
        self.post_project("raclette")
        self.post_project("tartiflette")
        data = self.client.get("/raclette/").data.decode("utf-8")
        assert data.count('href="/tartiflette/"') == 1

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
        assert 'href="/raclette/"' in data

        # Second join shouldn't add a double link
        self.client.get(invite_link)
        data = self.client.get("/tartiflette/").data.decode("utf-8")
        assert data.count('href="/raclette/"') == 1

    def test_invalid_invite_link_with_feed_token(self):
        """Test that a 'feed' token is not valid to join a project"""
        self.post_project("raclette")
        project = self.get_project("raclette")
        invite_link = url_for(
            ".join_project", project_id="raclette", token=project.generate_token("feed")
        )
        response = self.client.get(invite_link, follow_redirects=True)
        assert "Provided token is invalid" in response.data.decode()

    def test_invite_code_invalidation(self):
        """Test that invitation link expire after code change"""
        self.login("raclette")
        self.post_project("raclette")
        response = self.client.get("/raclette/invite").data.decode("utf-8")
        link = extract_link(response, "give them the following invitation link")

        self.client.post("/exit")
        response = self.client.get(link)
        # Link is valid
        assert response.status_code == 302

        # Change password to invalidate token
        # Other data are required, but useless for the test
        response = self.client.post(
            "/raclette/edit",
            data={
                "name": "raclette",
                "contact_email": "zorglub@notmyidea.org",
                "current_password": "raclette",
                "password": "didoudida",
                "default_currency": "XXX",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert "alert-danger" not in response.data.decode("utf-8")

        self.client.post("/exit")
        response = self.client.get(link, follow_redirects=True)
        # Link is invalid
        assert "Provided token is invalid" in response.data.decode("utf-8")

    def test_password_reminder(self):
        # test that it is possible to have an email containing the password of a
        # project in case people forget it (and it happens!)

        self.create_project("raclette")

        with self.app.mail.record_messages() as outbox:
            # a nonexisting project should not send an email
            self.client.post("/password-reminder", data={"id": "unexisting"})
            assert len(outbox) == 0

            # a mail should be sent when a project exists
            self.client.post("/password-reminder", data={"id": "raclette"})
            assert len(outbox) == 1
            assert "raclette" in outbox[0].body
            assert "raclette@notmyidea.org" in outbox[0].recipients

    def test_password_reset(self):
        # test that a password can be changed using a link sent by mail

        self.create_project("raclette")
        # Get password resetting link from mail
        with self.app.mail.record_messages() as outbox:
            resp = self.client.post(
                "/password-reminder", data={"id": "raclette"}, follow_redirects=True
            )
            # Check that we are redirected to the right page
            assert (
                "A link to reset your password has been sent to you"
                in resp.data.decode("utf-8")
            )
            # Check that an email was sent
            assert len(outbox) == 1
            url_start = outbox[0].body.find("You can reset it here: ") + 23
            url_end = outbox[0].body.find(".\n", url_start)
            url = outbox[0].body[url_start:url_end]
        # Test that we got a valid token
        resp = self.client.get(url)
        assert "Password confirmation</label>" in resp.data.decode("utf-8")
        # Test that password can be changed
        self.client.post(
            url, data={"password": "pass", "password_confirmation": "pass"}
        )
        resp = self.login("raclette", password="pass")
        assert "<title>Account manager - raclette</title>" in resp.data.decode("utf-8")
        # Test empty and null tokens
        resp = self.client.get("/reset-password")
        assert "No token provided" in resp.data.decode("utf-8")
        resp = self.client.get("/reset-password?token=token")
        assert "Invalid token" in resp.data.decode("utf-8")

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
                assert len(outbox) == 1
                assert outbox[0].recipients == ["raclette@notmyidea.org"]
                assert "A reminder email has just been sent to you" in resp.data.decode(
                    "utf-8"
                )

            # session is updated
            assert session["raclette"]

            # project is created
            assert len(models.Project.query.all()) == 1

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
            assert len(models.Project.query.all()) == 1

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
            assert "raclette" not in session

            # project is not created
            assert len(models.Project.query.all()) == 0

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
            assert session["raclette"]

            # project is created
            assert len(models.Project.query.all()) == 1

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
            assert len(models.Project.query.all()) == 1

            # Check that we can't delete project with a GET or with a
            # password-less POST.
            resp = self.client.get("/raclette/delete")
            assert resp.status_code == 405
            self.client.post("/raclette/delete")
            assert len(models.Project.query.all()) == 1

            # Delete for real
            c.post(
                "/raclette/delete",
                data={"password": "party"},
            )

            # project removed
            assert len(models.Project.query.all()) == 0

    def test_bill_placeholder(self):
        self.post_project("raclette")
        self.login("raclette")

        result = self.client.get("/raclette/")

        # Empty bill list and no participant, should now propose to add participants first
        assert (
            '<a href="/raclette/members/add">Add the first participant'
            in result.data.decode("utf-8")
        )

        result = self.client.post("/raclette/members/add", data={"name": "zorglub"})

        result = self.client.get("/raclette/")

        # Empty bill with member, list should now propose to add bills
        assert '<a href="/raclette/add"' in result.data.decode("utf-8")
        assert "Add your first bill" in result.data.decode("utf-8")

    def test_membership(self):
        self.post_project("raclette")
        self.login("raclette")

        # adds a member to this project
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        assert len(self.get_project("raclette").members) == 1

        # adds him twice
        result = self.client.post("/raclette/members/add", data={"name": "zorglub"})

        # should not accept him
        assert len(self.get_project("raclette").members) == 1

        # add fred
        self.client.post("/raclette/members/add", data={"name": "fred"})
        assert len(self.get_project("raclette").members) == 2

        # check fred is present in the bills page
        result = self.client.get("/raclette/")
        assert "fred" in result.data.decode("utf-8")

        # remove fred
        self.client.post(
            "/raclette/members/%s/delete" % self.get_project("raclette").members[-1].id
        )

        # as fred is not bound to any bill, he is removed
        assert len(self.get_project("raclette").members) == 1

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
        assert len(self.get_project("raclette").members) == 2
        assert len(self.get_project("raclette").active_members) == 1

        # as fred is now deactivated, check that he is not listed when adding
        # a bill or displaying the balance
        result = self.client.get("/raclette/")
        assert (f"/raclette/members/{fred_id}/delete") not in result.data.decode(
            "utf-8"
        )

        result = self.client.get("/raclette/add")
        assert "fred" not in result.data.decode("utf-8")

        # adding him again should reactivate him
        self.client.post("/raclette/members/add", data={"name": "fred"})
        assert len(self.get_project("raclette").active_members) == 2

        # adding an user with the same name as another user from a different
        # project should not cause any troubles
        self.post_project("randomid")
        self.login("randomid")
        self.client.post("/randomid/members/add", data={"name": "fred"})
        assert len(self.get_project("randomid").active_members) == 1

    def test_person_model(self):
        self.post_project("raclette")
        self.login("raclette")

        # adds a member to this project
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        zorglub = self.get_project("raclette").members[-1]

        # should not have any bills
        assert not zorglub.has_bills()

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
        assert zorglub.has_bills()

    def test_member_delete_method(self):
        self.post_project("raclette")
        self.login("raclette")

        # adds a member to this project
        self.client.post("/raclette/members/add", data={"name": "zorglub"})

        # try to remove the member using GET method
        response = self.client.get("/raclette/members/1/delete")
        assert response.status_code == 405

        # delete user using POST method
        self.client.post("/raclette/members/1/delete")
        assert len(self.get_project("raclette").active_members) == 0
        # try to delete an user already deleted
        self.client.post("/raclette/members/1/delete")

    def test_demo(self):
        # test that a demo project is created if none is defined
        assert [] == models.Project.query.all()
        self.client.get("/demo")
        demo = self.get_project("demo")
        assert demo is not None

        assert ["Amina", "Georg", "Alice"] == [m.name for m in demo.members]
        assert demo.get_bills().count() == 3

    def test_deactivated_demo(self):
        self.app.config["ACTIVATE_DEMO_PROJECT"] = False

        # test redirection to the create project form when demo is deactivated
        resp = self.client.get("/demo")
        assert '<a href="/create?project_id=demo">' in resp.data.decode("utf-8")

    def test_authentication(self):
        # try to authenticate without credentials should redirect
        # to the authentication page
        resp = self.client.post("/authenticate")
        assert "Authentication" in resp.data.decode("utf-8")

        # raclette that the login / logout process works
        self.create_project("raclette")

        # try to see the project while not being authenticated should redirect
        # to the authentication page
        resp = self.client.get("/raclette", follow_redirects=True)
        assert "Authentication" in resp.data.decode("utf-8")

        # try to connect with wrong credentials should not work
        with self.client as c:
            resp = c.post("/authenticate", data={"id": "raclette", "password": "nope"})

            assert "Authentication" in resp.data.decode("utf-8")
            assert "raclette" not in session

        # try to connect with the right credentials should work
        with self.client as c:
            resp = c.post(
                "/authenticate", data={"id": "raclette", "password": "raclette"}
            )

            assert "Authentication" not in resp.data.decode("utf-8")
            assert "raclette" in session
            assert session["raclette"]

            # logout should work with POST only
            resp = c.get("/exit")
            self.assertStatus(405, resp)

            # logout should wipe the session out
            c.post("/exit")
            assert "raclette" not in session

        # test that with admin credentials, one can access every project
        self.app.config["ADMIN_PASSWORD"] = generate_password_hash("pass")
        with self.client as c:
            resp = c.post("/admin?goto=%2Fraclette", data={"admin_password": "pass"})
            assert "Authentication" not in resp.data.decode("utf-8")
            assert session["is_admin"]

    def test_authentication_with_upper_case(self):
        self.post_project("Raclette")

        # try to connect with the right credentials should work
        with self.client as c:
            resp = c.post(
                "/authenticate", data={"id": "Raclette", "password": "Raclette"}
            )

            assert "Authentication" not in resp.data.decode("utf-8")
            assert "raclette" in session
            assert session["raclette"]

    def test_admin_authentication(self):
        self.app.config["ADMIN_PASSWORD"] = generate_password_hash("pass")
        # Disable public project creation so we have an admin endpoint to test
        self.app.config["ALLOW_PUBLIC_PROJECT_CREATION"] = False

        # test the redirection to the authentication page when trying to access admin endpoints
        resp = self.client.get("/create")
        assert '<a href="/admin?goto=%2Fcreate">' in resp.data.decode("utf-8")

        # test right password
        resp = self.client.post(
            "/admin?goto=%2Fcreate", data={"admin_password": "pass"}
        )
        assert '<a href="/create">/create</a>' in resp.data.decode("utf-8")

        # test wrong password
        resp = self.client.post(
            "/admin?goto=%2Fcreate", data={"admin_password": "wrong"}
        )
        assert '<a href="/create">/create</a>' not in resp.data.decode("utf-8")

        # test empty password
        resp = self.client.post("/admin?goto=%2Fcreate", data={"admin_password": ""})
        assert '<a href="/create">/create</a>' not in resp.data.decode("utf-8")

    def test_login_throttler(self):
        self.app.config["ADMIN_PASSWORD"] = generate_password_hash("pass")

        # Activate admin login throttling by authenticating 4 times with a wrong passsword
        self.client.post("/admin?goto=%2Fcreate", data={"admin_password": "wrong"})
        self.client.post("/admin?goto=%2Fcreate", data={"admin_password": "wrong"})
        self.client.post("/admin?goto=%2Fcreate", data={"admin_password": "wrong"})
        resp = self.client.post(
            "/admin?goto=%2Fcreate", data={"admin_password": "wrong"}
        )

        assert "Too many failed login attempts." in resp.data.decode("utf-8")
        # Try with limiter disabled
        from ihatemoney.utils import limiter

        try:
            limiter.enabled = False
            resp = self.client.post(
                "/admin?goto=%2Fcreate", data={"admin_password": "wrong"}
            )
            assert "Too many failed login attempts." not in resp.data.decode("utf-8")
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
        assert bill.amount == 25

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
        assert bill.amount == 10, "bill edition"

        # Try to delete the bill with a GET: it should fail
        response = self.client.get(f"/raclette/delete/{bill.id}")
        assert response.status_code == 405
        assert 1 == len(models.Bill.query.all()), "bill deletion"
        # Really delete the bill
        self.client.post(f"/raclette/delete/{bill.id}")
        assert 0 == len(models.Bill.query.all()), "bill deletion"

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
        assert set(balance.values()) == set([19.0, -19.0])

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
        assert bill.amount == -25

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
        assert bill.amount == 25.02

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
        assert bill.external_link == "https://example.com/fromage"

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
        assert "Invalid URL" in resp.data.decode("utf-8")

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
        assert set(balance.values()) == set([6, -6])

    def test_trimmed_members(self):
        self.post_project("raclette")

        # Add two times the same person (with a space at the end).
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "zorglub "})
        members = self.get_project("raclette").members

        assert len(members) == 1

    def test_weighted_members_list(self):
        self.post_project("raclette")

        # add two participants
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "tata", "weight": 1})

        resp = self.client.get("/raclette/")
        assert "extra-info" in resp.data.decode("utf-8")

        self.client.post(
            "/raclette/members/add", data={"name": "freddy familly", "weight": 4}
        )

        resp = self.client.get("/raclette/")
        assert "extra-info" not in resp.data.decode("utf-8")

    def test_negative_weight(self):
        self.post_project("raclette")

        # Add one user and edit it to have a negative share
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        resp = self.client.post(
            "/raclette/members/1/edit", data={"name": "zorglub", "weight": -1}
        )

        # An error should be generated, and its weight should still be 1.
        assert '<p class="alert alert-danger">' in resp.data.decode("utf-8")
        assert len(self.get_project("raclette").members) == 1
        assert self.get_project("raclette").members[0].weight == 1

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
            assert round(value, 2) == result[key]

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

        # It should fail if we don't provide the current password
        resp = self.client.post("/raclette/edit", data=new_data, follow_redirects=False)
        assert "This field is required" in resp.data.decode("utf-8")
        project = self.get_project("raclette")
        assert project.name != new_data["name"]
        assert project.contact_email != new_data["contact_email"]
        assert project.default_currency != new_data["default_currency"]
        assert not check_password_hash(project.password, new_data["password"])

        # It should fail if we provide the wrong current password
        new_data["current_password"] = "patates au fromage"
        resp = self.client.post("/raclette/edit", data=new_data, follow_redirects=False)
        assert "Invalid private code" in resp.data.decode("utf-8")
        project = self.get_project("raclette")
        assert project.name != new_data["name"]
        assert project.contact_email != new_data["contact_email"]
        assert project.default_currency != new_data["default_currency"]
        assert not check_password_hash(project.password, new_data["password"])

        # It should work if we give the current private code
        new_data["current_password"] = "raclette"
        resp = self.client.post("/raclette/edit", data=new_data)
        assert resp.status_code == 302
        project = self.get_project("raclette")
        assert project.name == new_data["name"]
        assert project.contact_email == new_data["contact_email"]
        assert project.default_currency == new_data["default_currency"]
        assert check_password_hash(project.password, new_data["password"])

        # Editing a project with a wrong email address should fail
        new_data["contact_email"] = "wrong_email"

        resp = self.client.post("/raclette/edit", data=new_data)
        assert "Invalid email address" in resp.data.decode("utf-8")

    def test_dashboard(self):
        # test that the dashboard is deactivated by default
        resp = self.client.post(
            "/admin?goto=%2Fdashboard",
            data={"admin_password": "adminpass"},
            follow_redirects=True,
        )
        assert '<div class="alert alert-danger">' in resp.data.decode("utf-8")

        # test access to the dashboard when it is activated
        self.enable_admin()
        resp = self.client.get("/dashboard")
        assert """<thead>
        <tr>
            <th>Project</th>
            <th>Number of participants</th>""" in resp.data.decode(
            "utf-8"
        )

    def test_dashboard_project_deletion(self):
        self.post_project("raclette")
        self.enable_admin()
        resp = self.client.get("/dashboard")
        pattern = re.compile(r"<form id=\"delete-project\" [^>]*?action=\"(.*?)\"")
        match = pattern.search(resp.data.decode("utf-8"))
        assert match is not None
        assert match.group(1) is not None

        resp = self.client.post(match.group(1))

        # project removed
        assert len(models.Project.query.all()) == 0

    def test_statistics_page(self):
        self.post_project("raclette")
        response = self.client.get("/raclette/statistics")
        assert response.status_code == 200

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
        assert len(project.active_months_range()) == 0
        assert len(project.monthly_stats) == 0

        # Check that the "monthly expenses" table is empty
        response = self.client.get("/raclette/statistics")
        regex = (
            r"<table id=\"monthly_stats\".*>\s*<thead>\s*<tr>\s*<th>Period</th>\s*"
            r"<th>Spent</th>\s*</tr>\s*</thead>\s*<tbody>\s*</tbody>\s*</table>"
        )
        assert re.search(regex, response.data.decode("utf-8"))

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
        assert re.search(
            regex.format("zorglub", r"\$20\.00", r"\$31\.67"),
            response.data.decode("utf-8"),
        )
        assert re.search(
            regex.format("fred", r"\$20\.00", r"\$5\.83"), response.data.decode("utf-8")
        )
        assert re.search(
            regex.format("tata", r"\$0\.00", r"\$2\.50"), response.data.decode("utf-8")
        )
        assert re.search(
            regex.format("pépé", r"\$0\.00", r"\$0\.00"), response.data.decode("utf-8")
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
        assert re.search(re.compile(regex1, re.DOTALL), response.data.decode("utf-8"))
        assert re.search(re.compile(regex2, re.DOTALL), response.data.decode("utf-8"))

        # Check monthly expenses again: it should have a single month and the correct amount
        august = datetime.date(year=2011, month=8, day=1)
        assert project.active_months_range() == [august]
        assert dict(project.monthly_stats[2011]) == {8: 40.0}

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
        assert project.active_months_range() == months
        assert dict(project.monthly_stats[2011]) == amounts_2011

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
        assert project.active_months_range() == months
        assert dict(project.monthly_stats[2011]) == amounts_2011

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
        assert project.active_months_range() == months
        assert dict(project.monthly_stats[2011]) == amounts_2011

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
        assert project.active_months_range() == months
        assert dict(project.monthly_stats[2011]) == amounts_2011

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
        assert project.active_months_range() == months
        assert dict(project.monthly_stats[2011]) == amounts_2011
        assert dict(project.monthly_stats[2012]) == amounts_2012

    def test_settle_page(self):
        self.post_project("raclette")
        response = self.client.get("/raclette/settle_bills")
        assert response.status_code == 200

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
            assert abs(a - balance[m.id]) < 0.01
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
            assert (
                0.0 != rounded_amount
            ), f"{t['amount']} is equal to zero after rounding"

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
        assert raclette.get_bills().count() == 1

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
        assert bill.what == "fromage à raclette"

        # Use the correct credentials to modify and delete the bill.
        # This ensures that modifying and deleting the bill can actually work

        self.client.post("/exit")
        self.client.post(
            "/authenticate", data={"id": "raclette", "password": "raclette"}
        )
        self.client.post("/raclette/edit/1", data=modified_bill)
        bill = models.Bill.query.filter(models.Bill.id == 1).one_or_none()
        assert bill is not None, "bill not found"
        assert bill.what == "roblochon"
        self.client.post("/raclette/delete/1")
        bill = models.Bill.query.filter(models.Bill.id == 1).one_or_none()
        assert bill is None

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
        assert member is not None, "member not found"
        assert member.name == "zorglub"
        assert member.activated

        # Use the correct credentials to modify and delete the member.
        # This ensures that modifying and deleting the member can actually work
        self.client.post("/exit")
        self.client.post(
            "/authenticate", data={"id": "raclette", "password": "raclette"}
        )
        self.client.post("/raclette/members/1/edit", data=modified_member)
        member = models.Person.query.filter(models.Person.id == 1).one()
        assert member.name == "bulgroz"
        self.client.post("/raclette/members/1/delete")
        member = models.Person.query.filter(models.Person.id == 1).one_or_none()
        assert member is None

    @pytest.mark.skip(reason="Currency conversion is broken")
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
            assert bill.original_currency == CurrencyConverter.no_currency
            assert bill.amount == bill.converted_amount

        # Then, switch to EUR, all bills must have been changed to this currency
        project.switch_currency("EUR")
        for bill in project.get_bills():
            assert bill.original_currency == "EUR"
            assert bill.amount == bill.converted_amount

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
        assert last_bill.converted_amount == last_bill.amount

        # Erase all currencies
        project.switch_currency(CurrencyConverter.no_currency)
        for bill in project.get_bills():
            assert bill.original_currency == CurrencyConverter.no_currency
            assert bill.amount == bill.converted_amount

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
        assert last_bill.converted_amount == expected_amount

        # Switch to USD. Now, NO bill should be in USD, since they already had a currency
        project.switch_currency("USD")
        for bill in project.get_bills():
            assert bill.original_currency != "USD"
            expected_amount = self.converter.exchange_currency(
                bill.amount, bill.original_currency, "USD"
            )
            assert bill.converted_amount == expected_amount

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
        assert '<p class="alert alert-danger">' in resp.data.decode("utf-8")
        assert self.get_project("raclette").default_currency == "USD"

    @pytest.mark.skip(reason="Currency conversion is broken")
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
        assert (
            self.converter.exchange_currency(bill.amount, "EUR", "USD")
            == bill.converted_amount
        )

        # And switch project to the currency from the bill we created
        project.switch_currency("EUR")
        bill = project.get_bills().first()
        assert bill.converted_amount == bill.amount

    @pytest.mark.skip(reason="Currency conversion is broken")
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
            assert (
                self.converter.exchange_currency(bill.amount, "EUR", "USD")
                == bill.converted_amount
            )

        # And switch project to no currency: amount should be equal to what was submitted
        project.switch_currency(CurrencyConverter.no_currency)
        no_currency_bills = [
            (bill.amount, bill.converted_amount) for bill in project.get_bills()
        ]
        assert no_currency_bills == [(5.0, 5.0), (10.0, 10.0)]

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
                "original_currency": "XXX",
            },
        )

        # Bill should have been accepted
        project = self.get_project("raclette")
        assert project.get_bills().count() == 1
        last_bill = project.get_bills().first()
        assert last_bill.amount == 0

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
        assert 'zorglub<span class="light">(x1)</span>' in resp.data.decode("utf-8")
        assert 'tata<span class="light">(x1.1)</span>' in resp.data.decode("utf-8")
        assert 'fred<span class="light">(x1.15)</span>' in resp.data.decode("utf-8")

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
        assert '<p class="alert alert-danger">' in resp.data.decode("utf-8")

        # Without any check, the following request will fail.
        resp = self.client.get("/raclette/")
        # No bills, the previous one was not added
        assert "No bills" in resp.data.decode("utf-8")

    def test_session_projects_migration_to_list(self):
        """In https://github.com/spiral-project/ihatemoney/pull/1082, session["projects"]
        was migrated from a list to a dict. We need to handle this.
        """
        self.post_project("raclette")
        self.client.get("/exit")

        with self.client as c:
            c.post("/authenticate", data={"id": "raclette", "password": "raclette"})
            assert session["raclette"]
            # New behavior
            assert isinstance(session["projects"], dict)
            # Now, go back to the past
            with c.session_transaction() as sess:
                sess["projects"] = [("raclette", "raclette")]
            # It should convert entry to dict
            c.get("/")
            assert isinstance(session["projects"], dict)
            assert "raclette" in session["projects"]

    def test_rss_feed(self):
        """
        Tests that the RSS feed output content is expected.
        """
        with fake_time("2023-07-25 12:00:00"):
            self.post_project("raclette", default_currency="EUR")
            self.client.post("/raclette/members/add", data={"name": "george"})
            self.client.post("/raclette/members/add", data={"name": "peter"})
            self.client.post("/raclette/members/add", data={"name": "steven"})

            self.client.post(
                "/raclette/add",
                data={
                    "date": "2016-12-31",
                    "what": "fromage à raclette",
                    "payer": 1,
                    "payed_for": [1, 2, 3],
                    "amount": "12",
                    "original_currency": "EUR",
                },
            )
            self.client.post(
                "/raclette/add",
                data={
                    "date": "2016-12-30",
                    "what": "charcuterie",
                    "payer": 2,
                    "payed_for": [1, 2],
                    "amount": "15",
                    "original_currency": "EUR",
                },
            )
            self.client.post(
                "/raclette/add",
                data={
                    "date": "2016-12-29",
                    "what": "vin blanc",
                    "payer": 2,
                    "payed_for": [1, 2],
                    "amount": "10",
                    "original_currency": "EUR",
                },
            )

        project = self.get_project("raclette")
        token = project.generate_token("feed")
        resp = self.client.get(f"/raclette/feed/{token}.xml")

        expected_rss_content = f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:atom="http://www.w3.org/2005/Atom"
    >
    <channel>
        <title>I Hate Money — raclette</title>
        <description>Latest bills from raclette</description>
        <atom:link href="http://localhost/raclette/feed/{token}.xml" rel="self" type="application/rss+xml" />
        <link>http://localhost/raclette/</link>
        <item>
            <title>fromage à raclette - €12.00</title>
            <guid isPermaLink="false">1</guid>
            <dc:creator>george</dc:creator>
            <description>December 31, 2016 - george, peter, steven : €4.00</description>
            <pubDate>Tue, 25 Jul 2023 00:00:00 +0000</pubDate>
        </item>
        <item>
            <title>charcuterie - €15.00</title>
            <guid isPermaLink="false">2</guid>
            <dc:creator>peter</dc:creator>
            <description>December 30, 2016 - george, peter : €7.50</description>
            <pubDate>Tue, 25 Jul 2023 00:00:00 +0000</pubDate>
        </item>
        <item>
            <title>vin blanc - €10.00</title>
            <guid isPermaLink="false">3</guid>
            <dc:creator>peter</dc:creator>
            <description>December 29, 2016 - george, peter : €5.00</description>
            <pubDate>Tue, 25 Jul 2023 00:00:00 +0000</pubDate>
        </item>
        </channel>
</rss>"""  # noqa: E501
        assert resp.data.decode() == expected_rss_content

    def test_rss_feed_history_disabled(self):
        """
        Tests that RSS feeds is correctly rendered even if the project
        history is disabled.
        """
        with fake_time("2023-07-25 12:00:00"):
            self.post_project("raclette", default_currency="EUR", project_history=False)
            self.client.post("/raclette/members/add", data={"name": "george"})
            self.client.post("/raclette/members/add", data={"name": "peter"})
            self.client.post("/raclette/members/add", data={"name": "steven"})

            self.client.post(
                "/raclette/add",
                data={
                    "date": "2016-12-31",
                    "what": "fromage à raclette",
                    "payer": 1,
                    "payed_for": [1, 2, 3],
                    "amount": "12",
                    "original_currency": "EUR",
                },
            )
            self.client.post(
                "/raclette/add",
                data={
                    "date": "2016-12-30",
                    "what": "charcuterie",
                    "payer": 2,
                    "payed_for": [1, 2],
                    "amount": "15",
                    "original_currency": "EUR",
                },
            )
            self.client.post(
                "/raclette/add",
                data={
                    "date": "2016-12-29",
                    "what": "vin blanc",
                    "payer": 2,
                    "payed_for": [1, 2],
                    "amount": "10",
                    "original_currency": "EUR",
                },
            )

        project = self.get_project("raclette")
        token = project.generate_token("feed")
        resp = self.client.get(f"/raclette/feed/{token}.xml")

        expected_rss_content = f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:atom="http://www.w3.org/2005/Atom"
    >
    <channel>
        <title>I Hate Money — raclette</title>
        <description>Latest bills from raclette</description>
        <atom:link href="http://localhost/raclette/feed/{token}.xml" rel="self" type="application/rss+xml" />
        <link>http://localhost/raclette/</link>
        <item>
            <title>fromage à raclette - €12.00</title>
            <guid isPermaLink="false">1</guid>
            <dc:creator>george</dc:creator>
            <description>December 31, 2016 - george, peter, steven : €4.00</description>
            <pubDate>Tue, 25 Jul 2023 00:00:00 +0000</pubDate>
        </item>
        <item>
            <title>charcuterie - €15.00</title>
            <guid isPermaLink="false">2</guid>
            <dc:creator>peter</dc:creator>
            <description>December 30, 2016 - george, peter : €7.50</description>
            <pubDate>Tue, 25 Jul 2023 00:00:00 +0000</pubDate>
        </item>
        <item>
            <title>vin blanc - €10.00</title>
            <guid isPermaLink="false">3</guid>
            <dc:creator>peter</dc:creator>
            <description>December 29, 2016 - george, peter : €5.00</description>
            <pubDate>Tue, 25 Jul 2023 00:00:00 +0000</pubDate>
        </item>
        </channel>
</rss>"""  # noqa: E501
        assert resp.data.decode() == expected_rss_content

    def test_rss_if_modified_since_header(self):
        # Project creation
        with fake_time("2023-07-26 13:00:00"):
            self.post_project("raclette")
            self.client.post("/raclette/members/add", data={"name": "george"})
            project = self.get_project("raclette")
            token = project.generate_token("feed")

            resp = self.client.get(f"/raclette/feed/{token}.xml")
            assert resp.status_code == 200
            assert resp.headers.get("Last-Modified") == "Wed, 26 Jul 2023 13:00:00 UTC"

        resp = self.client.get(
            f"/raclette/feed/{token}.xml",
            headers={"If-Modified-Since": "Tue, 26 Jul 2023 12:00:00 UTC"},
        )
        assert resp.status_code == 200

        resp = self.client.get(
            f"/raclette/feed/{token}.xml",
            headers={"If-Modified-Since": "Tue, 26 Jul 2023 14:00:00 UTC"},
        )
        assert resp.status_code == 304

        # Add bill
        with fake_time("2023-07-27 13:00:00"):
            self.login("raclette")
            resp = self.client.post(
                "/raclette/add",
                data={
                    "date": "2016-12-31",
                    "what": "fromage à raclette",
                    "payer": 1,
                    "payed_for": [1],
                    "amount": "12",
                    "original_currency": "XXX",
                },
                follow_redirects=True,
            )
            assert resp.status_code == 200
            assert "The bill has been added" in resp.data.decode()

        resp = self.client.get(
            f"/raclette/feed/{token}.xml",
            headers={"If-Modified-Since": "Tue, 27 Jul 2023 12:00:00 UTC"},
        )
        assert resp.headers.get("Last-Modified") == "Thu, 27 Jul 2023 13:00:00 UTC"
        assert resp.status_code == 200

        resp = self.client.get(
            f"/raclette/feed/{token}.xml",
            headers={"If-Modified-Since": "Tue, 27 Jul 2023 14:00:00 UTC"},
        )
        assert resp.status_code == 304

    def test_rss_etag_headers(self):
        # Project creation
        with fake_time("2023-07-26 13:00:00"):
            self.post_project("raclette")
            self.client.post("/raclette/members/add", data={"name": "george"})
            project = self.get_project("raclette")
            token = project.generate_token("feed")

            resp = self.client.get(f"/raclette/feed/{token}.xml")
            assert resp.headers.get("ETag") == build_etag(
                project.id, "2023-07-26T13:00:00"
            )
            assert resp.status_code == 200

        resp = self.client.get(
            f"/raclette/feed/{token}.xml",
            headers={
                "If-None-Match": build_etag(project.id, "2023-07-26T12:00:00"),
            },
        )
        assert resp.status_code == 200

        resp = self.client.get(
            f"/raclette/feed/{token}.xml",
            headers={
                "If-None-Match": build_etag(project.id, "2023-07-26T13:00:00"),
            },
        )
        assert resp.status_code == 304

        # Add bill
        with fake_time("2023-07-27 13:00:00"):
            self.login("raclette")
            resp = self.client.post(
                "/raclette/add",
                data={
                    "date": "2016-12-31",
                    "what": "fromage à raclette",
                    "payer": 1,
                    "payed_for": [1],
                    "amount": "12",
                    "original_currency": "XXX",
                },
                follow_redirects=True,
            )
            assert resp.status_code == 200
            assert "The bill has been added" in resp.data.decode()

        resp = self.client.get(
            f"/raclette/feed/{token}.xml",
            headers={
                "If-None-Match": build_etag(project.id, "2023-07-27T12:00:00"),
            },
        )
        assert resp.headers.get("ETag") == build_etag(project.id, "2023-07-27T13:00:00")
        assert resp.status_code == 200

        resp = self.client.get(
            f"/raclette/feed/{token}.xml",
            headers={
                "If-None-Match": build_etag(project.id, "2023-07-27T13:00:00"),
            },
        )
        assert resp.status_code == 304

    def test_rss_feed_bad_token(self):
        self.post_project("raclette")
        project = self.get_project("raclette")
        token = project.generate_token("feed")

        resp = self.client.get(f"/raclette/feed/{token}.xml")
        assert resp.status_code == 200
        resp = self.client.get("/raclette/feed/invalid-token.xml")
        assert resp.status_code == 404

    def test_rss_feed_different_project_with_same_password(
        self,
    ):
        """
        Test that a 'feed' token is not valid to access the feed of
        another project with the same password.
        """
        self.post_project("raclette", password="password")
        self.post_project("reblochon", password="password")
        project = self.get_project("raclette")
        token = project.generate_token("feed")

        resp = self.client.get(f"/reblochon/feed/{token}.xml")
        assert resp.status_code == 404

    def test_rss_feed_different_project_with_different_password(
        self,
    ):
        """
        Test that a 'feed' token is not valid to access the feed of
        another project with a different password.
        """
        self.post_project("raclette", password="password")
        self.post_project("reblochon", password="another-password")
        project = self.get_project("raclette")
        token = project.generate_token("feed")

        resp = self.client.get(f"/reblochon/feed/{token}.xml")
        assert resp.status_code == 404

    def test_rss_feed_invalidated_token(self):
        """
        Tests that a feed URL becames invalid when the project password changes.
        """
        self.post_project("raclette")
        project = self.get_project("raclette")
        token = project.generate_token("feed")

        resp = self.client.get(f"/raclette/feed/{token}.xml")
        assert resp.status_code == 200

        self.client.post(
            "/raclette/edit",
            data={
                "name": "raclette",
                "contact_email": "zorglub@notmyidea.org",
                "current_password": "raclette",
                "password": "didoudida",
                "default_currency": "XXX",
            },
            follow_redirects=True,
        )

        resp = self.client.get(f"/raclette/feed/{token}.xml")
        assert resp.status_code == 404

    def test_remember_payer_per_project(self):
        """
        Tests that the last payer is remembered for each project
        """
        self.post_project("raclette")
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "fred"})
        members_ids = [m.id for m in self.get_project("raclette").members]
        # create a bill
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": members_ids[1],
                "payed_for": members_ids,
                "amount": "25",
            },
        )

        self.post_project("tartiflette")
        self.client.post("/tartiflette/members/add", data={"name": "pluton"})
        self.client.post("/tartiflette/members/add", data={"name": "mars"})
        self.client.post("/tartiflette/members/add", data={"name": "venus"})
        members_ids_tartif = [m.id for m in self.get_project("tartiflette").members]
        # create a bill
        self.client.post(
            "/tartiflette/add",
            data={
                "date": "2011-08-12",
                "what": "fromage à tartiflette spatial",
                "payer": members_ids_tartif[2],
                "payed_for": members_ids_tartif,
                "amount": "24",
            },
        )

        with self.client as c:
            c.post("/authenticate", data={"id": "raclette", "password": "raclette"})
            assert isinstance(session["last_selected_payer_per_project"], dict)
            assert "raclette" in session["last_selected_payer_per_project"]
            assert "tartiflette" in session["last_selected_payer_per_project"]
            assert (
                session["last_selected_payer_per_project"]["raclette"] == members_ids[1]
            )
            assert (
                session["last_selected_payer_per_project"]["tartiflette"]
                == members_ids_tartif[2]
            )

    def test_remember_payed_for(self):
        """
        Tests that the last ower is remembered
        """
        self.post_project("raclette")
        self.client.post("/raclette/members/add", data={"name": "zorglub"})
        self.client.post("/raclette/members/add", data={"name": "fred"})
        self.client.post("/raclette/members/add", data={"name": "pipistrelle"})
        members_ids = [m.id for m in self.get_project("raclette").members]
        # create a bill
        self.client.post(
            "/raclette/add",
            data={
                "date": "2011-08-10",
                "what": "fromage à raclette",
                "payer": members_ids[1],
                "payed_for": members_ids[1:],
                "amount": "25",
            },
        )

        with self.client as c:
            c.post("/authenticate", data={"id": "raclette", "password": "raclette"})
            assert isinstance(session["last_selected_payed_for"], dict)
            assert "raclette" in session["last_selected_payed_for"]
            assert session["last_selected_payed_for"]["raclette"] == members_ids[1:]
