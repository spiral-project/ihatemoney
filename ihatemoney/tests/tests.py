# -*- coding: utf-8 -*-
from __future__ import unicode_literals
try:
    import unittest2 as unittest
except ImportError:
    import unittest  # NOQA
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

import os
import json
from collections import defaultdict
import six
from time import sleep

from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
from flask_testing import TestCase

from ihatemoney.run import create_app, db, load_configuration
from ihatemoney.manage import GenerateConfig, GeneratePasswordHash
from ihatemoney import models
from ihatemoney import utils

# Unset configuration file env var if previously set
os.environ.pop('IHATEMONEY_SETTINGS_FILE_PATH', None)

__HERE__ = os.path.dirname(os.path.abspath(__file__))


class BaseTestCase(TestCase):

    SECRET_KEY = "TEST SESSION"

    def create_app(self):
        # Pass the test object as a configuration.
        return create_app(self)

    def setUp(self):
        db.create_all()

    def tearDown(self):
        # clean after testing
        db.session.remove()
        db.drop_all()

    def login(self, project, password=None, test_client=None):
        password = password or project

        return self.client.post('/authenticate', data=dict(
            id=project, password=password), follow_redirects=True)

    def post_project(self, name):
        """Create a fake project"""
        # create the project
        self.client.post("/create", data={
            'name': name,
            'id': name,
            'password': name,
            'contact_email': '%s@notmyidea.org' % name
        })

    def create_project(self, name):
        project = models.Project(
            id=name,
            name=six.text_type(name),
            password=generate_password_hash(name),
            contact_email="%s@notmyidea.org" % name)
        models.db.session.add(project)
        models.db.session.commit()


class IhatemoneyTestCase(BaseTestCase):
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    TESTING = True
    WTF_CSRF_ENABLED = False  # Simplifies the tests.

    def assertStatus(self, expected, resp, url=""):
        return self.assertEqual(expected, resp.status_code,
                                "%s expected %s, got %s" % (url, expected, resp.status_code))


class ConfigurationTestCase(BaseTestCase):

    def test_default_configuration(self):
        """Test that default settings are loaded when no other configuration file is specified"""
        self.assertFalse(self.app.config['DEBUG'])
        self.assertEqual(self.app.config['SQLALCHEMY_DATABASE_URI'], 'sqlite:////tmp/ihatemoney.db')
        self.assertFalse(self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'])
        self.assertEqual(self.app.config['MAIL_DEFAULT_SENDER'],
                         ("Budget manager", "budget@notmyidea.org"))

    def test_env_var_configuration_file(self):
        """Test that settings are loaded from the specified configuration file"""
        os.environ['IHATEMONEY_SETTINGS_FILE_PATH'] = os.path.join(__HERE__,
                                                                   "ihatemoney_envvar.cfg")
        load_configuration(self.app)
        self.assertEqual(self.app.config['SECRET_KEY'], 'lalatra')

        # Test that the specified configuration file is loaded
        # even if the default configuration file ihatemoney.cfg exists
        os.environ['IHATEMONEY_SETTINGS_FILE_PATH'] = os.path.join(__HERE__,
                                                                   "ihatemoney_envvar.cfg")
        self.app.config.root_path = __HERE__
        load_configuration(self.app)
        self.assertEqual(self.app.config['SECRET_KEY'], 'lalatra')

        os.environ.pop('IHATEMONEY_SETTINGS_FILE_PATH', None)

    def test_default_configuration_file(self):
        """Test that settings are loaded from the default configuration file"""
        self.app.config.root_path = __HERE__
        load_configuration(self.app)
        self.assertEqual(self.app.config['SECRET_KEY'], 'supersecret')


class BudgetTestCase(IhatemoneyTestCase):

    def test_notifications(self):
        """Test that the notifications are sent, and that email adresses
        are checked properly.
        """
        # sending a message to one person
        with self.app.mail.record_messages() as outbox:

            # create a project
            self.login("raclette")

            self.post_project("raclette")
            self.client.post("/raclette/invite",
                             data={"emails": 'alexis@notmyidea.org'})

            self.assertEqual(len(outbox), 2)
            self.assertEqual(outbox[0].recipients, ["raclette@notmyidea.org"])
            self.assertEqual(outbox[1].recipients, ["alexis@notmyidea.org"])

        # sending a message to multiple persons
        with self.app.mail.record_messages() as outbox:
            self.client.post("/raclette/invite",
                             data={"emails": 'alexis@notmyidea.org, toto@notmyidea.org'})

            # only one message is sent to multiple persons
            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0].recipients,
                             ["alexis@notmyidea.org", "toto@notmyidea.org"])

        # mail address checking
        with self.app.mail.record_messages() as outbox:
            response = self.client.post("/raclette/invite",
                                        data={"emails": "toto"})
            self.assertEqual(len(outbox), 0)  # no message sent
            self.assertIn("The email toto is not valid", response.data.decode('utf-8'))

        # mixing good and wrong adresses shouldn't send any messages
        with self.app.mail.record_messages() as outbox:
            self.client.post("/raclette/invite",
                             data={"emails": 'alexis@notmyidea.org, alexis'})  # not valid

            # only one message is sent to multiple persons
            self.assertEqual(len(outbox), 0)

    def test_invite(self):
        """Test that invitation e-mails are sent properly
        """
        self.login("raclette")
        self.post_project("raclette")
        with self.app.mail.record_messages() as outbox:
            self.client.post("/raclette/invite",
                             data={"emails": 'toto@notmyidea.org'})
            self.assertEqual(len(outbox), 1)
            url_start = outbox[0].body.find('You can log in using this link: ') + 32
            url_end = outbox[0].body.find('.\n', url_start)
            url = outbox[0].body[url_start:url_end]
        self.client.get("/exit")
        # Test that we got a valid token
        resp = self.client.get(url, follow_redirects=True)
        self.assertIn('You probably want to <a href="/raclette/add"', resp.data.decode('utf-8'))
        # Test empty and invalid tokens
        self.client.get("/exit")
        resp = self.client.get("/authenticate")
        self.assertIn("You either provided a bad token", resp.data.decode('utf-8'))
        resp = self.client.get("/authenticate?token=token")
        self.assertIn("You either provided a bad token", resp.data.decode('utf-8'))

    def test_password_reminder(self):
        # test that it is possible to have an email cotaining the password of a
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
            self.client.post("/password-reminder", data={"id": "raclette"})
            self.assertEqual(len(outbox), 1)
            url_start = outbox[0].body.find('You can reset it here: ') + 23
            url_end = outbox[0].body.find('.\n', url_start)
            url = outbox[0].body[url_start:url_end]
        # Test that we got a valid token
        resp = self.client.get(url)
        self.assertIn("Password confirmation</label>", resp.data.decode('utf-8'))
        # Test that password can be changed
        self.client.post(url, data={'password': 'pass', 'password_confirmation': 'pass'})
        resp = self.login('raclette', password='pass')
        self.assertIn("<title>Account manager - raclette</title>", resp.data.decode('utf-8'))
        # Test empty and null tokens
        resp = self.client.get("/reset-password")
        self.assertIn("No token provided", resp.data.decode('utf-8'))
        resp = self.client.get("/reset-password?token=token")
        self.assertIn("Invalid token", resp.data.decode('utf-8'))

    def test_project_creation(self):
        with self.app.test_client() as c:

            # add a valid project
            c.post("/create", data={
                'name': 'The fabulous raclette party',
                'id': 'raclette',
                'password': 'party',
                'contact_email': 'raclette@notmyidea.org'
            })

            # session is updated
            self.assertTrue(session['raclette'])

            # project is created
            self.assertEqual(len(models.Project.query.all()), 1)

            # Add a second project with the same id
            models.Project.query.get('raclette')

            c.post("/create", data={
                'name': 'Another raclette party',
                'id': 'raclette',  # already used !
                'password': 'party',
                'contact_email': 'raclette@notmyidea.org'
            })

            # no new project added
            self.assertEqual(len(models.Project.query.all()), 1)

    def test_project_deletion(self):

        with self.app.test_client() as c:
            c.post("/create", data={
                'name': 'raclette party',
                'id': 'raclette',
                'password': 'party',
                'contact_email': 'raclette@notmyidea.org'
            })

            # project added
            self.assertEqual(len(models.Project.query.all()), 1)

            c.get('/raclette/delete')

            # project removed
            self.assertEqual(len(models.Project.query.all()), 0)

    def test_membership(self):
        self.post_project("raclette")
        self.login("raclette")

        # adds a member to this project
        self.client.post("/raclette/members/add", data={'name': 'alexis'})
        self.assertEqual(len(models.Project.query.get("raclette").members), 1)

        # adds him twice
        result = self.client.post("/raclette/members/add",
                                  data={'name': 'alexis'})

        # should not accept him
        self.assertEqual(len(models.Project.query.get("raclette").members), 1)

        # add fred
        self.client.post("/raclette/members/add", data={'name': 'fred'})
        self.assertEqual(len(models.Project.query.get("raclette").members), 2)

        # check fred is present in the bills page
        result = self.client.get("/raclette/")
        self.assertIn("fred", result.data.decode('utf-8'))

        # remove fred
        self.client.post("/raclette/members/%s/delete" %
                         models.Project.query.get("raclette").members[-1].id)

        # as fred is not bound to any bill, he is removed
        self.assertEqual(len(models.Project.query.get("raclette").members), 1)

        # add fred again
        self.client.post("/raclette/members/add", data={'name': 'fred'})
        fred_id = models.Project.query.get("raclette").members[-1].id

        # bound him to a bill
        result = self.client.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': 'fromage à raclette',
            'payer': fred_id,
            'payed_for': [fred_id, ],
            'amount': '25',
        })

        # remove fred
        self.client.post("/raclette/members/%s/delete" % fred_id)

        # he is still in the database, but is deactivated
        self.assertEqual(len(models.Project.query.get("raclette").members), 2)
        self.assertEqual(
            len(models.Project.query.get("raclette").active_members), 1)

        # as fred is now deactivated, check that he is not listed when adding
        # a bill or displaying the balance
        result = self.client.get("/raclette/")
        self.assertNotIn(("/raclette/members/%s/delete" % fred_id), result.data.decode('utf-8'))

        result = self.client.get("/raclette/add")
        self.assertNotIn("fred", result.data.decode('utf-8'))

        # adding him again should reactivate him
        self.client.post("/raclette/members/add", data={'name': 'fred'})
        self.assertEqual(
            len(models.Project.query.get("raclette").active_members), 2)

        # adding an user with the same name as another user from a different
        # project should not cause any troubles
        self.post_project("randomid")
        self.login("randomid")
        self.client.post("/randomid/members/add", data={'name': 'fred'})
        self.assertEqual(
            len(models.Project.query.get("randomid").active_members), 1)

    def test_person_model(self):
        self.post_project("raclette")
        self.login("raclette")

        # adds a member to this project
        self.client.post("/raclette/members/add", data={'name': 'alexis'})
        alexis = models.Project.query.get("raclette").members[-1]

        # should not have any bills
        self.assertFalse(alexis.has_bills())

        # bound him to a bill
        self.client.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': 'fromage à raclette',
            'payer': alexis.id,
            'payed_for': [alexis.id, ],
            'amount': '25',
        })

        # should have a bill now
        alexis = models.Project.query.get("raclette").members[-1]
        self.assertTrue(alexis.has_bills())

    def test_member_delete_method(self):
        self.post_project("raclette")
        self.login("raclette")

        # adds a member to this project
        self.client.post("/raclette/members/add", data={'name': 'alexis'})

        # try to remove the member using GET method
        response = self.client.get("/raclette/members/1/delete")
        self.assertEqual(response.status_code, 405)

        # delete user using POST method
        self.client.post("/raclette/members/1/delete")
        self.assertEqual(
            len(models.Project.query.get("raclette").active_members), 0)
        # try to delete an user already deleted
        self.client.post("/raclette/members/1/delete")

    def test_demo(self):
        # test that a demo project is created if none is defined
        self.assertEqual([], models.Project.query.all())
        self.client.get("/demo")
        self.assertTrue(models.Project.query.get("demo") is not None)

    def test_deactivated_demo(self):
        self.app.config['ACTIVATE_DEMO_PROJECT'] = False

        # test redirection to the create project form when demo is deactivated
        resp = self.client.get("/demo")
        self.assertIn('<a href="/create?project_id=demo">', resp.data.decode('utf-8'))

    def test_authentication(self):
        # try to authenticate without credentials should redirect
        # to the authentication page
        resp = self.client.post("/authenticate")
        self.assertIn("Authentication", resp.data.decode('utf-8'))

        # raclette that the login / logout process works
        self.create_project("raclette")

        # try to see the project while not being authenticated should redirect
        # to the authentication page
        resp = self.client.get("/raclette", follow_redirects=True)
        self.assertIn("Authentication", resp.data.decode('utf-8'))

        # try to connect with wrong credentials should not work
        with self.app.test_client() as c:
            resp = c.post("/authenticate",
                          data={'id': 'raclette', 'password': 'nope'})

            self.assertIn("Authentication", resp.data.decode('utf-8'))
            self.assertNotIn('raclette', session)

        # try to connect with the right credentials should work
        with self.app.test_client() as c:
            resp = c.post("/authenticate",
                          data={'id': 'raclette', 'password': 'raclette'})

            self.assertNotIn("Authentication", resp.data.decode('utf-8'))
            self.assertIn('raclette', session)
            self.assertTrue(session['raclette'])

            # logout should wipe the session out
            c.get("/exit")
            self.assertNotIn('raclette', session)

        # test that with admin credentials, one can access every project
        self.app.config['ADMIN_PASSWORD'] = generate_password_hash("pass")
        with self.app.test_client() as c:
            resp = c.post("/admin?goto=%2Fraclette", data={'admin_password': 'pass'})
            self.assertNotIn("Authentication", resp.data.decode('utf-8'))
            self.assertTrue(session['is_admin'])

    def test_admin_authentication(self):
        self.app.config['ADMIN_PASSWORD'] = generate_password_hash("pass")
        # Disable public project creation so we have an admin endpoint to test
        self.app.config['ALLOW_PUBLIC_PROJECT_CREATION'] = False

        # test the redirection to the authentication page when trying to access admin endpoints
        resp = self.client.get("/create")
        self.assertIn('<a href="/admin?goto=%2Fcreate">', resp.data.decode('utf-8'))

        # test right password
        resp = self.client.post("/admin?goto=%2Fcreate", data={'admin_password': 'pass'})
        self.assertIn('<a href="/create">/create</a>', resp.data.decode('utf-8'))

        # test wrong password
        resp = self.client.post("/admin?goto=%2Fcreate", data={'admin_password': 'wrong'})
        self.assertNotIn('<a href="/create">/create</a>', resp.data.decode('utf-8'))

        # test empty password
        resp = self.client.post("/admin?goto=%2Fcreate", data={'admin_password': ''})
        self.assertNotIn('<a href="/create">/create</a>', resp.data.decode('utf-8'))

    def test_login_throttler(self):
        self.app.config['ADMIN_PASSWORD'] = generate_password_hash("pass")

        # Activate admin login throttling by authenticating 4 times with a wrong passsword
        self.client.post("/admin?goto=%2Fcreate", data={'admin_password': 'wrong'})
        self.client.post("/admin?goto=%2Fcreate", data={'admin_password': 'wrong'})
        self.client.post("/admin?goto=%2Fcreate", data={'admin_password': 'wrong'})
        resp = self.client.post("/admin?goto=%2Fcreate", data={'admin_password': 'wrong'})

        self.assertIn('Too many failed login attempts, please retry later.',
                      resp.data.decode('utf-8'))
        # Change throttling delay
        import gc
        for obj in gc.get_objects():
            if isinstance(obj, utils.LoginThrottler):
                obj._delay = 0.005
                break
        # Wait for delay to expire and retry logging in
        sleep(1)
        resp = self.client.post("/admin?goto=%2Fcreate", data={'admin_password': 'wrong'})
        self.assertNotIn('Too many failed login attempts, please retry later.',
                         resp.data.decode('utf-8'))

    def test_manage_bills(self):
        self.post_project("raclette")

        # add two persons
        self.client.post("/raclette/members/add", data={'name': 'alexis'})
        self.client.post("/raclette/members/add", data={'name': 'fred'})

        members_ids = [m.id for m in
                       models.Project.query.get("raclette").members]

        # create a bill
        self.client.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': 'fromage à raclette',
            'payer': members_ids[0],
            'payed_for': members_ids,
            'amount': '25',
        })
        models.Project.query.get("raclette")
        bill = models.Bill.query.one()
        self.assertEqual(bill.amount, 25)

        # edit the bill
        self.client.post("/raclette/edit/%s" % bill.id, data={
            'date': '2011-08-10',
            'what': 'fromage à raclette',
            'payer': members_ids[0],
            'payed_for': members_ids,
            'amount': '10',
        })

        bill = models.Bill.query.one()
        self.assertEqual(bill.amount, 10, "bill edition")

        # delete the bill
        self.client.get("/raclette/delete/%s" % bill.id)
        self.assertEqual(0, len(models.Bill.query.all()), "bill deletion")

        # test balance
        self.client.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': 'fromage à raclette',
            'payer': members_ids[0],
            'payed_for': members_ids,
            'amount': '19',
        })

        self.client.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': 'fromage à raclette',
            'payer': members_ids[1],
            'payed_for': members_ids[0],
            'amount': '20',
        })

        self.client.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': 'fromage à raclette',
            'payer': members_ids[1],
            'payed_for': members_ids,
            'amount': '17',
        })

        balance = models.Project.query.get("raclette").balance
        self.assertEqual(set(balance.values()), set([19.0, -19.0]))

        # Bill with negative amount
        self.client.post("/raclette/add", data={
            'date': '2011-08-12',
            'what': 'fromage à raclette',
            'payer': members_ids[0],
            'payed_for': members_ids,
            'amount': '-25'
        })
        bill = models.Bill.query.filter(models.Bill.date == '2011-08-12')[0]
        self.assertEqual(bill.amount, -25)

        # add a bill with a comma
        self.client.post("/raclette/add", data={
            'date': '2011-08-01',
            'what': 'fromage à raclette',
            'payer': members_ids[0],
            'payed_for': members_ids,
            'amount': '25,02',
        })
        bill = models.Bill.query.filter(models.Bill.date == '2011-08-01')[0]
        self.assertEqual(bill.amount, 25.02)

    def test_weighted_balance(self):
        self.post_project("raclette")

        # add two persons
        self.client.post("/raclette/members/add", data={'name': 'alexis'})
        self.client.post("/raclette/members/add", data={'name': 'freddy familly', 'weight': 4})

        members_ids = [m.id for m in
                       models.Project.query.get("raclette").members]

        # test balance
        self.client.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': 'fromage à raclette',
            'payer': members_ids[0],
            'payed_for': members_ids,
            'amount': '10',
        })

        self.client.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': 'pommes de terre',
            'payer': members_ids[1],
            'payed_for': members_ids,
            'amount': '10',
        })

        balance = models.Project.query.get("raclette").balance
        self.assertEqual(set(balance.values()), set([6, -6]))


    def test_trimmed_members(self):
        self.post_project("raclette")

        # add two times the same person (with a space at the end)
        self.client.post("/raclette/members/add", data={'name': 'alexis'})
        self.client.post("/raclette/members/add", data={'name': 'alexis '})
        members = models.Project.query.get("raclette").members

        self.assertEqual(len(members), 1)

    def test_weighted_members_list(self):
        self.post_project("raclette")

        # add two persons
        self.client.post("/raclette/members/add", data={'name': 'alexis'})
        self.client.post("/raclette/members/add", data={'name': 'tata', 'weight': 1})

        resp = self.client.get("/raclette/")
        self.assertIn('extra-info', resp.data.decode('utf-8'))

        self.client.post("/raclette/members/add", data={'name': 'freddy familly', 'weight': 4})

        resp = self.client.get("/raclette/")
        self.assertNotIn('extra-info', resp.data.decode('utf-8'))

    def test_negative_weight(self):
        self.post_project("raclette")

        # Add one user and edit it to have a negative share
        self.client.post("/raclette/members/add", data={'name': 'alexis'})
        resp = self.client.post("/raclette/members/1/edit", data={'name': 'alexis', 'weight': -1})

        # An error should be generated, and its weight should still be 1.
        self.assertIn('<p class="alert alert-danger">', resp.data.decode('utf-8'))
        self.assertEqual(len(models.Project.query.get('raclette').members), 1)
        self.assertEqual(models.Project.query.get('raclette').members[0].weight, 1)

    def test_rounding(self):
        self.post_project("raclette")

        # add members
        self.client.post("/raclette/members/add", data={'name': 'alexis'})
        self.client.post("/raclette/members/add", data={'name': 'fred'})
        self.client.post("/raclette/members/add", data={'name': 'tata'})

        # create bills
        self.client.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': 'fromage à raclette',
            'payer': 1,
            'payed_for': [1, 2, 3],
            'amount': '24.36',
        })

        self.client.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': 'red wine',
            'payer': 2,
            'payed_for': [1],
            'amount': '19.12',
        })

        self.client.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': 'delicatessen',
            'payer': 1,
            'payed_for': [1, 2],
            'amount': '22',
        })

        balance = models.Project.query.get("raclette").balance
        result = {}
        result[models.Project.query.get("raclette").members[0].id] = 8.12
        result[models.Project.query.get("raclette").members[1].id] = 0.0
        result[models.Project.query.get("raclette").members[2].id] = -8.12
        # Since we're using floating point to store currency, we can have some
        # rounding issues that prevent test from working.
        # However, we should obtain the same values as the theorical ones if we
        # round to 2 decimals, like in the UI.
        for key, value in six.iteritems(balance):
            self.assertEqual(round(value, 2), result[key])

    def test_edit_project(self):
        # A project should be editable

        self.post_project("raclette")
        new_data = {
            'name': 'Super raclette party!',
            'contact_email': 'alexis@notmyidea.org',
            'password': 'didoudida'
        }

        resp = self.client.post("/raclette/edit", data=new_data,
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        project = models.Project.query.get("raclette")

        self.assertEqual(project.name, new_data['name'])
        self.assertEqual(project.contact_email, new_data['contact_email'])
        self.assertTrue(check_password_hash(project.password, new_data['password']))

        # Editing a project with a wrong email address should fail
        new_data['contact_email'] = 'wrong_email'

        resp = self.client.post("/raclette/edit", data=new_data,
                                follow_redirects=True)
        self.assertIn("Invalid email address", resp.data.decode('utf-8'))

    def test_dashboard(self):
        # test that the dashboard is deactivated by default
        resp = self.client.post(
            "/admin?goto=%2Fdashboard",
            data={'admin_password': 'adminpass'},
            follow_redirects=True
        )
        self.assertIn('<div class="alert alert-danger">', resp.data.decode('utf-8'))

        # test access to the dashboard when it is activated
        self.app.config['ACTIVATE_ADMIN_DASHBOARD'] = True
        self.app.config['ADMIN_PASSWORD'] = generate_password_hash("adminpass")
        resp = self.client.post(
            "/admin?goto=%2Fdashboard",
            data={'admin_password': 'adminpass'},
            follow_redirects=True
        )
        self.assertIn('<thead><tr><th>Project</th><th>Number of members', resp.data.decode('utf-8'))

    def test_statistics_page(self):
        self.post_project("raclette")
        response = self.client.get("/raclette/statistics")
        self.assertEqual(response.status_code, 200)

    def test_statistics(self):
        self.post_project("raclette")

        # add members
        self.client.post("/raclette/members/add", data={'name': 'alexis', 'weight': 2})
        self.client.post("/raclette/members/add", data={'name': 'fred'})
        self.client.post("/raclette/members/add", data={'name': 'tata'})
        # Add a member with a balance=0 :
        self.client.post("/raclette/members/add", data={'name': 'toto'})

        # create bills
        self.client.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': 'fromage à raclette',
            'payer': 1,
            'payed_for': [1, 2, 3],
            'amount': '10.0',
        })

        self.client.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': 'red wine',
            'payer': 2,
            'payed_for': [1],
            'amount': '20',
        })

        self.client.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': 'delicatessen',
            'payer': 1,
            'payed_for': [1, 2],
            'amount': '10',
        })

        response = self.client.get("/raclette/statistics")
        self.assertIn("<td>alexis</td>\n        "
                      + "<td>20.00</td>\n        "
                      + "<td>31.67</td>\n        "
                      + "<td>-11.67</td>\n",
                      response.data.decode('utf-8'))
        self.assertIn("<td>fred</td>\n        "
                      + "<td>20.00</td>\n        "
                      + "<td>5.83</td>\n        "
                      + "<td>14.17</td>\n",
                      response.data.decode('utf-8'))
        self.assertIn("<td>tata</td>\n        "
                      + "<td>0.00</td>\n        "
                      + "<td>2.50</td>\n        "
                      + "<td>-2.50</td>\n",
                      response.data.decode('utf-8'))
        self.assertIn("<td>toto</td>\n        "
                      + "<td>0.00</td>\n        "
                      + "<td>0.00</td>\n        "
                      + "<td>0.00</td>\n",
                      response.data.decode('utf-8'))

    def test_settle_page(self):
        self.post_project("raclette")
        response = self.client.get("/raclette/settle_bills")
        self.assertEqual(response.status_code, 200)

    def test_settle(self):
        self.post_project("raclette")

        # add members
        self.client.post("/raclette/members/add", data={'name': 'alexis'})
        self.client.post("/raclette/members/add", data={'name': 'fred'})
        self.client.post("/raclette/members/add", data={'name': 'tata'})
        # Add a member with a balance=0 :
        self.client.post("/raclette/members/add", data={'name': 'toto'})

        # create bills
        self.client.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': 'fromage à raclette',
            'payer': 1,
            'payed_for': [1, 2, 3],
            'amount': '10.0',
        })

        self.client.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': 'red wine',
            'payer': 2,
            'payed_for': [1],
            'amount': '20',
        })

        self.client.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': 'delicatessen',
            'payer': 1,
            'payed_for': [1, 2],
            'amount': '10',
        })
        project = models.Project.query.get('raclette')
        transactions = project.get_transactions_to_settle_bill()
        members = defaultdict(int)
        # We should have the same values between transactions and project balances
        for t in transactions:
            members[t['ower']] -= t['amount']
            members[t['receiver']] += t['amount']
        balance = models.Project.query.get("raclette").balance
        for m, a in members.items():
            self.assertEqual(a, balance[m.id])
        return

    def test_settle_zero(self):
        self.post_project("raclette")

        # add members
        self.client.post("/raclette/members/add", data={'name': 'alexis'})
        self.client.post("/raclette/members/add", data={'name': 'fred'})
        self.client.post("/raclette/members/add", data={'name': 'tata'})

        # create bills
        self.client.post("/raclette/add", data={
            'date': '2016-12-31',
            'what': 'fromage à raclette',
            'payer': 1,
            'payed_for': [1, 2, 3],
            'amount': '10.0',
        })

        self.client.post("/raclette/add", data={
            'date': '2016-12-31',
            'what': 'red wine',
            'payer': 2,
            'payed_for': [1, 3],
            'amount': '20',
        })

        self.client.post("/raclette/add", data={
            'date': '2017-01-01',
            'what': 'refund',
            'payer': 3,
            'payed_for': [2],
            'amount': '13.33',
        })
        project = models.Project.query.get('raclette')
        transactions = project.get_transactions_to_settle_bill()

        # There should not be any zero-amount transfer after rounding
        for t in transactions:
            rounded_amount = round(t['amount'], 2)
            self.assertNotEqual(0.0, rounded_amount,
                                msg='%f is equal to zero after rounding' % t['amount'])

    def test_export(self):
        self.post_project("raclette")

        # add members
        self.client.post("/raclette/members/add", data={'name': 'alexis', 'weight': 2})
        self.client.post("/raclette/members/add", data={'name': 'fred'})
        self.client.post("/raclette/members/add", data={'name': 'tata'})
        self.client.post("/raclette/members/add", data={'name': 'pépé'})

        # create bills
        self.client.post("/raclette/add", data={
            'date': '2016-12-31',
            'what': 'fromage à raclette',
            'payer': 1,
            'payed_for': [1, 2, 3, 4],
            'amount': '10.0',
        })

        self.client.post("/raclette/add", data={
            'date': '2016-12-31',
            'what': 'red wine',
            'payer': 2,
            'payed_for': [1, 3],
            'amount': '200',
        })

        self.client.post("/raclette/add", data={
            'date': '2017-01-01',
            'what': 'refund',
            'payer': 3,
            'payed_for': [2],
            'amount': '13.33',
        })

        # generate json export of bills
        resp = self.client.post("/raclette/edit", data={
            'export_format': 'json',
            'export_type': 'bills'
        })
        expected = [{
            'date': '2017-01-01',
            'what': 'refund',
            'amount': 13.33,
            'payer_name': 'tata',
            'payer_weight': 1.0,
            'owers': ['fred']
        }, {
            'date': '2016-12-31',
            'what': 'red wine',
            'amount': 200.0,
            'payer_name': 'fred',
            'payer_weight': 1.0,
            'owers': ['alexis', 'tata']
        }, {
            'date': '2016-12-31',
            'what': 'fromage \xe0 raclette',
            'amount': 10.0,
            'payer_name': 'alexis',
            'payer_weight': 2.0,
            'owers': ['alexis', 'fred', 'tata', 'p\xe9p\xe9']
        }]
        self.assertEqual(json.loads(resp.data.decode('utf-8')), expected)

        # generate csv export of bills
        resp = self.client.post("/raclette/edit", data={
            'export_format': 'csv',
            'export_type': 'bills'
        })
        expected = [
            "date,what,amount,payer_name,payer_weight,owers",
            "2017-01-01,refund,13.33,tata,1.0,fred",
            "2016-12-31,red wine,200.0,fred,1.0,\"alexis, tata\"",
            "2016-12-31,fromage à raclette,10.0,alexis,2.0,\"alexis, fred, tata, pépé\""]
        received_lines = resp.data.decode('utf-8').split("\n")

        for i, line in enumerate(expected):
            self.assertEqual(
                set(line.split(",")),
                set(received_lines[i].strip("\r").split(","))
            )

        # generate json export of transactions
        resp = self.client.post("/raclette/edit", data={
            'export_format': 'json',
            'export_type': 'transactions'
        })
        expected = [{"amount": 127.33, "receiver": "fred", "ower": "alexis"},
                    {"amount": 55.34, "receiver": "fred", "ower": "tata"},
                    {"amount": 2.00, "receiver": "fred", "ower": "p\xe9p\xe9"}]
        self.assertEqual(json.loads(resp.data.decode('utf-8')), expected)

        # generate csv export of transactions
        resp = self.client.post("/raclette/edit", data={
            'export_format': 'csv',
            'export_type': 'transactions'
        })

        expected = ["amount,receiver,ower",
                    "127.33,fred,alexis",
                    "55.34,fred,tata",
                    "2.0,fred,pépé"]
        received_lines = resp.data.decode('utf-8').split("\n")

        for i, line in enumerate(expected):
            self.assertEqual(
                set(line.split(",")),
                set(received_lines[i].strip("\r").split(","))
            )

        # wrong export_format should return a 200 and export form
        resp = self.client.post("/raclette/edit", data={
            'export_format': 'wrong_export_format',
            'export_type': 'transactions'
        })

        self.assertEqual(resp.status_code, 200)
        self.assertIn('id="export_format" name="export_format"', resp.data.decode('utf-8'))

        # wrong export_type should return a 200 and export form
        resp = self.client.post("/raclette/edit", data={
            'export_format': 'json',
            'export_type': 'wrong_export_type'
        })

        self.assertEqual(resp.status_code, 200)
        self.assertIn('id="export_format" name="export_format"', resp.data.decode('utf-8'))


class APITestCase(IhatemoneyTestCase):

    """Tests the API"""

    def api_create(self, name, id=None, password=None, contact=None):
        id = id or name
        password = password or name
        contact = contact or "%s@notmyidea.org" % name

        return self.client.post("/api/projects", data={
            'name': name,
            'id': id,
            'password': password,
            'contact_email': contact
        })

    def api_add_member(self, project, name, weight=1):
        self.client.post("/api/projects/%s/members" % project,
                         data={"name": name, "weight": weight},
                         headers=self.get_auth(project))

    def get_auth(self, username, password=None):
        password = password or username
        base64string = utils.base64_encode(
            ('%s:%s' % (username, password)).encode('utf-8')).decode('utf-8').replace('\n', '')
        return {"Authorization": "Basic %s" % base64string}

    def test_basic_auth(self):
        # create a project
        resp = self.api_create("raclette")
        self.assertStatus(201, resp)

        # try to do something on it being unauth should return a 401
        resp = self.client.get("/api/projects/raclette")
        self.assertStatus(401, resp)

        # PUT / POST / DELETE / GET on the different resources
        # should also return a 401
        for verb in ('post',):
            for resource in ("/raclette/members", "/raclette/bills"):
                url = "/api/projects" + resource
                self.assertStatus(401, getattr(self.client, verb)(url),
                                  verb + resource)

        for verb in ('get', 'delete', 'put'):
            for resource in ("/raclette", "/raclette/members/1",
                             "/raclette/bills/1"):
                url = "/api/projects" + resource

                self.assertStatus(401, getattr(self.client, verb)(url),
                                  verb + resource)

    def test_project(self):
        # wrong email should return an error
        resp = self.client.post("/api/projects", data={
            'name': "raclette",
            'id': "raclette",
            'password': "raclette",
            'contact_email': "not-an-email"
        })

        self.assertTrue(400, resp.status_code)
        self.assertEqual('{"contact_email": ["Invalid email address."]}\n',
                         resp.data.decode('utf-8'))

        # create it
        resp = self.api_create("raclette")
        self.assertTrue(201, resp.status_code)

        # create it twice should return a 400
        resp = self.api_create("raclette")

        self.assertTrue(400, resp.status_code)
        self.assertIn('id', json.loads(resp.data.decode('utf-8')))

        # get information about it
        resp = self.client.get("/api/projects/raclette",
                               headers=self.get_auth("raclette"))

        self.assertTrue(200, resp.status_code)
        expected = {
            "active_members": [],
            "name": "raclette",
            "contact_email": "raclette@notmyidea.org",
            "members": [],
            "id": "raclette",
            "balance": {},
        }
        decoded_resp = json.loads(resp.data.decode('utf-8'))
        self.assertDictEqual(decoded_resp, expected)

        # edit should work
        resp = self.client.put("/api/projects/raclette", data={
            "contact_email": "yeah@notmyidea.org",
            "password": "raclette",
            "name": "The raclette party",
        }, headers=self.get_auth("raclette"))

        self.assertEqual(200, resp.status_code)

        resp = self.client.get("/api/projects/raclette",
                               headers=self.get_auth("raclette"))

        self.assertEqual(200, resp.status_code)
        expected = {
            "active_members": [],
            "name": "The raclette party",
            "contact_email": "yeah@notmyidea.org",
            "members": [],
            "id": "raclette",
            "balance": {},
        }
        decoded_resp = json.loads(resp.data.decode('utf-8'))
        self.assertDictEqual(decoded_resp, expected)

        # password change is possible via API
        resp = self.client.put("/api/projects/raclette", data={
            "contact_email": "yeah@notmyidea.org",
            "password": "tartiflette",
            "name": "The raclette party",
        }, headers=self.get_auth("raclette"))

        self.assertEqual(200, resp.status_code)

        resp = self.client.get("/api/projects/raclette",
                               headers=self.get_auth(
                                   "raclette", "tartiflette"))
        self.assertEqual(200, resp.status_code)

        # delete should work
        resp = self.client.delete("/api/projects/raclette",
                                  headers=self.get_auth(
                                      "raclette", "tartiflette"))

        # get should return a 401 on an unknown resource
        resp = self.client.get("/api/projects/raclette",
                               headers=self.get_auth("raclette"))
        self.assertEqual(401, resp.status_code)

    def test_member(self):
        # create a project
        self.api_create("raclette")

        # get the list of members (should be empty)
        req = self.client.get("/api/projects/raclette/members",
                              headers=self.get_auth("raclette"))

        self.assertStatus(200, req)
        self.assertEqual('[]\n', req.data.decode('utf-8'))

        # add a member
        req = self.client.post("/api/projects/raclette/members", data={
            "name": "Alexis"
        }, headers=self.get_auth("raclette"))

        # the id of the new member should be returned
        self.assertStatus(201, req)
        self.assertEqual("1\n", req.data.decode('utf-8'))

        # the list of members should contain one member
        req = self.client.get("/api/projects/raclette/members",
                              headers=self.get_auth("raclette"))

        self.assertStatus(200, req)
        self.assertEqual(len(json.loads(req.data.decode('utf-8'))), 1)

        # Try to add another member with the same name.
        req = self.client.post("/api/projects/raclette/members", data={
            "name": "Alexis"
        }, headers=self.get_auth("raclette"))
        self.assertStatus(400, req)

        # edit the member
        req = self.client.put("/api/projects/raclette/members/1", data={
            "name": "Fred",
            "weight": 2,
        }, headers=self.get_auth("raclette"))

        self.assertStatus(200, req)

        # get should return the new name
        req = self.client.get("/api/projects/raclette/members/1",
                              headers=self.get_auth("raclette"))

        self.assertStatus(200, req)
        self.assertEqual("Fred", json.loads(req.data.decode('utf-8'))["name"])
        self.assertEqual(2, json.loads(req.data.decode('utf-8'))["weight"])

        # edit this member with same information
        # (test PUT idemopotence)
        req = self.client.put("/api/projects/raclette/members/1", data={
            "name": "Fred"
        }, headers=self.get_auth("raclette"))

        self.assertStatus(200, req)

        # de-activate the user
        req = self.client.put("/api/projects/raclette/members/1", data={
            "name": "Fred",
            "activated": False,
        }, headers=self.get_auth("raclette"))
        self.assertStatus(200, req)

        req = self.client.get("/api/projects/raclette/members/1",
                              headers=self.get_auth("raclette"))
        self.assertStatus(200, req)
        self.assertEqual(False, json.loads(req.data.decode('utf-8'))["activated"])

        # re-activate the user
        req = self.client.put("/api/projects/raclette/members/1", data={
            "name": "Fred",
            "activated": True,
        }, headers=self.get_auth("raclette"))

        req = self.client.get("/api/projects/raclette/members/1",
                              headers=self.get_auth("raclette"))
        self.assertStatus(200, req)
        self.assertEqual(True, json.loads(req.data.decode('utf-8'))["activated"])

        # delete a member

        req = self.client.delete("/api/projects/raclette/members/1",
                                 headers=self.get_auth("raclette"))

        self.assertStatus(200, req)

        # the list of members should be empty
        req = self.client.get("/api/projects/raclette/members",
                              headers=self.get_auth("raclette"))

        self.assertStatus(200, req)
        self.assertEqual('[]\n', req.data.decode('utf-8'))

    def test_bills(self):
        # create a project
        self.api_create("raclette")

        # add members
        self.api_add_member("raclette", "alexis")
        self.api_add_member("raclette", "fred")
        self.api_add_member("raclette", "arnaud")

        # get the list of bills (should be empty)
        req = self.client.get("/api/projects/raclette/bills",
                              headers=self.get_auth("raclette"))
        self.assertStatus(200, req)

        self.assertEqual("[]\n", req.data.decode('utf-8'))

        # add a bill
        req = self.client.post("/api/projects/raclette/bills", data={
            'date': '2011-08-10',
            'what': 'fromage',
            'payer': "1",
            'payed_for': ["1", "2"],
            'amount': '25',
        }, headers=self.get_auth("raclette"))

        # should return the id
        self.assertStatus(201, req)
        self.assertEqual(req.data.decode('utf-8'), "1\n")

        # get this bill details
        req = self.client.get("/api/projects/raclette/bills/1",
                              headers=self.get_auth("raclette"))

        # compare with the added info
        self.assertStatus(200, req)
        expected = {
            "what": "fromage",
            "payer_id": 1,
            "owers": [
                {"activated": True, "id": 1, "name": "alexis", "weight": 1},
                {"activated": True, "id": 2, "name": "fred", "weight": 1}],
            "amount": 25.0,
            "date": "2011-08-10",
            "id": 1}

        self.assertDictEqual(expected, json.loads(req.data.decode('utf-8')))

        # the list of bills should length 1
        req = self.client.get("/api/projects/raclette/bills",
                              headers=self.get_auth("raclette"))
        self.assertStatus(200, req)
        self.assertEqual(1, len(json.loads(req.data.decode('utf-8'))))

        # edit with errors should return an error
        req = self.client.put("/api/projects/raclette/bills/1", data={
            'date': '201111111-08-10',  # not a date
            'what': 'fromage',
            'payer': "1",
            'payed_for': ["1", "2"],
            'amount': '25',
        }, headers=self.get_auth("raclette"))

        self.assertStatus(400, req)
        self.assertEqual('{"date": ["This field is required."]}\n', req.data.decode('utf-8'))

        # edit a bill
        req = self.client.put("/api/projects/raclette/bills/1", data={
            'date': '2011-09-10',
            'what': 'beer',
            'payer': "2",
            'payed_for': ["1", "2"],
            'amount': '25',
        }, headers=self.get_auth("raclette"))

        # check its fields
        req = self.client.get("/api/projects/raclette/bills/1",
                              headers=self.get_auth("raclette"))

        expected = {
            "what": "beer",
            "payer_id": 2,
            "owers": [
                {"activated": True, "id": 1, "name": "alexis", "weight": 1},
                {"activated": True, "id": 2, "name": "fred", "weight": 1}],
            "amount": 25.0,
            "date": "2011-09-10",
            "id": 1}

        self.assertDictEqual(expected, json.loads(req.data.decode('utf-8')))

        # delete a bill
        req = self.client.delete("/api/projects/raclette/bills/1",
                                 headers=self.get_auth("raclette"))
        self.assertStatus(200, req)

        # getting it should return a 404
        req = self.client.get("/api/projects/raclette/bills/1",
                              headers=self.get_auth("raclette"))
        self.assertStatus(404, req)

    def test_statistics(self):
        # create a project
        self.api_create("raclette")

        # add members
        self.api_add_member("raclette", "alexis")
        self.api_add_member("raclette", "fred")

        # add a bill
        req = self.client.post("/api/projects/raclette/bills", data={
            'date': '2011-08-10',
            'what': 'fromage',
            'payer': "1",
            'payed_for': ["1", "2"],
            'amount': '25',
        }, headers=self.get_auth("raclette"))

        # get the list of bills (should be empty)
        req = self.client.get("/api/projects/raclette/statistics",
                              headers=self.get_auth("raclette"))
        self.assertStatus(200, req)
        self.assertEqual([
            {'balance': 12.5,
             'member': {'activated': True, 'id': 1,
                        'name': 'alexis', 'weight': 1.0},
             'paid': 25.0,
             'spent': 12.5},
            {'balance': -12.5,
             'member': {'activated': True, 'id': 2,
                        'name': 'fred', 'weight': 1.0},
             'paid': 0,
             'spent': 12.5}],
            json.loads(req.data.decode('utf-8')))

    def test_username_xss(self):
        # create a project
        # self.api_create("raclette")
        self.post_project("raclette")
        self.login("raclette")

        # add members
        self.api_add_member("raclette", "<script>")

        result = self.client.get('/raclette/')
        self.assertNotIn("<script>", result.data.decode('utf-8'))

    def test_weighted_bills(self):
        # create a project
        self.api_create("raclette")

        # add members
        self.api_add_member("raclette", "alexis")
        self.api_add_member("raclette", "freddy familly", 4)
        self.api_add_member("raclette", "arnaud")

        # add a bill
        req = self.client.post("/api/projects/raclette/bills", data={
            'date': '2011-08-10',
            'what': "fromage",
            'payer': "1",
            'payed_for': ["1", "2"],
            'amount': '25',
        }, headers=self.get_auth("raclette"))

        # get this bill details
        req = self.client.get("/api/projects/raclette/bills/1",
                              headers=self.get_auth("raclette"))

        # compare with the added info
        self.assertStatus(200, req)
        expected = {
            "what": "fromage",
            "payer_id": 1,
            "owers": [
                {"activated": True, "id": 1, "name": "alexis", "weight": 1},
                {"activated": True, "id": 2, "name": "freddy familly", "weight": 4}],
            "amount": 25.0,
            "date": "2011-08-10",
            "id": 1}
        self.assertDictEqual(expected, json.loads(req.data.decode('utf-8')))

        # getting it should return a 404
        req = self.client.get("/api/projects/raclette",
                              headers=self.get_auth("raclette"))

        expected = {
            "active_members": [
                {"activated": True, "id": 1, "name": "alexis", "weight": 1.0},
                {"activated": True, "id": 2, "name": "freddy familly", "weight": 4.0},
                {"activated": True, "id": 3, "name": "arnaud", "weight": 1.0}
            ],
            "balance": {"1": 20.0, "2": -20.0, "3": 0},
            "contact_email": "raclette@notmyidea.org",
            "id": "raclette",

            "members": [
                {"activated": True, "id": 1, "name": "alexis", "weight": 1.0},
                {"activated": True, "id": 2, "name": "freddy familly", "weight": 4.0},
                {"activated": True, "id": 3, "name": "arnaud", "weight": 1.0}
            ],
            "name": "raclette"}

        self.assertStatus(200, req)
        decoded_req = json.loads(req.data.decode('utf-8'))
        self.assertDictEqual(decoded_req, expected)


class ServerTestCase(IhatemoneyTestCase):

    def test_homepage(self):
        # See https://github.com/spiral-project/ihatemoney/pull/358
        self.app.config['APPLICATION_ROOT'] = '/'
        req = self.client.get("/")
        self.assertStatus(200, req)

    def test_unprefixed(self):
        self.app.config['APPLICATION_ROOT'] = '/'
        req = self.client.get("/foo/")
        self.assertStatus(303, req)

    def test_prefixed(self):
        self.app.config['APPLICATION_ROOT'] = '/foo'
        req = self.client.get("/foo/")
        self.assertStatus(200, req)


class CommandTestCase(BaseTestCase):
    def test_generate_config(self):
        """ Simply checks that all config file generation
        - raise no exception
        - produce something non-empty
        """
        cmd = GenerateConfig()
        for config_file in cmd.get_options()[0].kwargs['choices']:
            with patch('sys.stdout', new=six.StringIO()) as stdout:
                cmd.run(config_file)
                print(stdout.getvalue())
                self.assertNotEqual(len(stdout.getvalue().strip()), 0)

    def test_generate_password_hash(self):
        cmd = GeneratePasswordHash()
        with patch('sys.stdout', new=six.StringIO()) as stdout, \
             patch('getpass.getpass', new=lambda prompt: 'secret'): # NOQA
            cmd.run()
            print(stdout.getvalue())
            self.assertEqual(len(stdout.getvalue().strip()), 187)


if __name__ == "__main__":
    unittest.main()
