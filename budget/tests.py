 # -*- coding: utf-8 -*-
import os
import tempfile
import unittest

from flask import session

import web
import models

class TestCase(unittest.TestCase):

    def setUp(self):
        web.app.config['TESTING'] = True

        web.app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///memory" 
        web.app.config['CSRF_ENABLED'] = False # simplify the tests
        self.app = web.app.test_client()

        models.db.init_app(web.app)
        web.mail.init_app(web.app)

        models.db.app = web.app
        models.db.create_all()

    def tearDown(self):
        # clean after testing
        models.db.session.remove()
        models.db.drop_all()

    def login(self, project, password=None, test_client=None):
        password = password or project
        test_client = test_client or self.app

        return test_client.post('/authenticate', data=dict(
            id=project, password=password), follow_redirects=True)

    def create_project(self, name):
        """Create a fake project"""
        # create the project
        self.app.post("/create", data={
                'name': name,
                'id': name,
                'password': name,
                'contact_email': '%s@notmyidea.org' % name
        })

class BudgetTestCase(TestCase):

    def test_notifications(self):
        """Test that the notifications are sent, and that email adresses
        are checked properly.
        """
        # sending a message to one person
        with web.mail.record_messages() as outbox:

            # create a project
            self.login("raclette")

            self.create_project("raclette")
            self.app.post("/raclette/invite", data=
                    {"emails": 'alexis@notmyidea.org'})

            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0].recipients, ["alexis@notmyidea.org"])

        # sending a message to multiple persons
        with web.mail.record_messages() as outbox:
            self.app.post("/raclette/invite", data=
                    {"emails": 'alexis@notmyidea.org, toto@notmyidea.org'})

            # only one message is sent to multiple persons
            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0].recipients, 
                    ["alexis@notmyidea.org", "toto@notmyidea.org"])

        # mail address checking
        with web.mail.record_messages() as outbox:
            response = self.app.post("/raclette/invite", data={"emails": "toto"})
            self.assertEqual(len(outbox), 0) # no message sent
            self.assertIn("The email toto is not valid", response.data)

        # mixing good and wrong adresses shouldn't send any messages
        with web.mail.record_messages() as outbox:
            self.app.post("/raclette/invite", data=
                    {"emails": 'alexis@notmyidea.org, alexis'}) # not valid

            # only one message is sent to multiple persons
            self.assertEqual(len(outbox), 0)


    def test_project_creation(self):
        with web.app.test_client() as c:

            # add a valid project
            c.post("/create", data={
                'name': 'The fabulous raclette party',
                'id': 'raclette',
                'password': 'party',
                'contact_email': 'raclette@notmyidea.org'
            })

            # session is updated
            self.assertEqual(session['raclette'], 'party')
        
            # project is created
            self.assertEqual(len(models.Project.query.all()), 1)

            # Add a second project with the same id
            models.Project.query.get('raclette')

            result = c.post("/create", data={
                'name': 'Another raclette party',
                'id': 'raclette', #already used !
                'password': 'party',
                'contact_email': 'raclette@notmyidea.org'
            })

            # no new project added
            self.assertEqual(len(models.Project.query.all()), 1)

    def test_membership(self):
        self.create_project("raclette")
        self.login("raclette")

        # adds a member to this project
        self.app.post("/raclette/members/add", data={'name': 'alexis' })
        self.assertEqual(len(models.Project.query.get("raclette").members), 1)

        # adds him twice
        result = self.app.post("/raclette/members/add", data={'name': 'alexis' })
        # should not accept him
        self.assertEqual(len(models.Project.query.get("raclette").members), 1)

        # add fred
        self.app.post("/raclette/members/add", data={'name': 'fred' })
        self.assertEqual(len(models.Project.query.get("raclette").members), 2)

        # check fred is present in the bills page
        result = self.app.get("/raclette/")
        self.assertIn("fred", result.data)
        
        # remove fred
        self.app.post("/raclette/members/%s/delete" % 
                models.Project.query.get("raclette").members[-1].id)

        # as fred is not bound to any bill, he is removed
        self.assertEqual(len(models.Project.query.get("raclette").members), 1)

        # add fred again
        self.app.post("/raclette/members/add", data={'name': 'fred' })
        fred_id = models.Project.query.get("raclette").members[-1].id

        # bound him to a bill
        result = self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'fromage à raclette',
            'payer': fred_id,
            'payed_for': [fred_id,],
            'amount': '25',
        })

        # remove fred
        self.app.post("/raclette/members/%s/delete" % fred_id)

        # he is still in the database, but is deactivated
        self.assertEqual(len(models.Project.query.get("raclette").members), 2)
        self.assertEqual(
                len(models.Project.query.get("raclette").active_members), 1)

        # as fred is now deactivated, check that he is not listed when adding
        # a bill or displaying the balance
        result = self.app.get("/raclette/")
        self.assertNotIn("/raclette/members/%s/delete" % fred_id, result.data)

        result = self.app.get("/raclette/add")
        self.assertNotIn("fred", result.data)

    def test_demo(self):
        # Test that it is possible to connect automatically by going onto /demo
        with web.app.test_client() as c:
            models.db.session.add(models.Project(id="demo", name=u"demonstration", 
                password="demo", contact_email="demo@notmyidea.org"))
            models.db.session.commit()
            c.get("/demo")

            # session is updated
            self.assertEqual(session['demo'], 'demo')

    def test_demo(self):
        # test that a demo project is created if none is defined
        with web.app.test_client() as c:
            self.assertEqual([], models.Project.query.all())
            c.get("/demo")
            self.assertTrue(models.Project.query.get("demo") is not None)


if __name__ == "__main__":
    unittest.main()
