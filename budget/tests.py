 # -*- coding: utf-8 -*-
import os
import tempfile
import unittest

from flask import session

import run
import models

class TestCase(unittest.TestCase):

    def setUp(self):
        run.app.config['TESTING'] = True

        run.app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///memory" 
        run.app.config['CSRF_ENABLED'] = False # simplify the tests
        self.app = run.app.test_client()

        models.db.init_app(run.app)
        run.mail.init_app(run.app)

        models.db.app = run.app
        models.db.create_all()

    def tearDown(self):
        # clean after testing
        models.db.session.remove()
        models.db.drop_all()

    def login(self, project, password=None, test_client=None):
        password = password or project

        return self.app.post('/authenticate', data=dict(
            id=project, password=password), follow_redirects=True)

    def post_project(self, name):
        """Create a fake project"""
        # create the project
        self.app.post("/create", data={
                'name': name,
                'id': name,
                'password': name,
                'contact_email': '%s@notmyidea.org' % name
        })

    def create_project(self, name):
        models.db.session.add(models.Project(id=name, name=unicode(name), 
            password=name, contact_email="%s@notmyidea.org" % name))
        models.db.session.commit()

class BudgetTestCase(TestCase):

    def test_notifications(self):
        """Test that the notifications are sent, and that email adresses
        are checked properly.
        """
        # sending a message to one person
        with run.mail.record_messages() as outbox:

            # create a project
            self.login("raclette")

            self.post_project("raclette")
            self.app.post("/raclette/invite", data=
                    {"emails": 'alexis@notmyidea.org'})

            self.assertEqual(len(outbox), 2)
            self.assertEqual(outbox[0].recipients, ["raclette@notmyidea.org"])
            self.assertEqual(outbox[1].recipients, ["alexis@notmyidea.org"])

        # sending a message to multiple persons
        with run.mail.record_messages() as outbox:
            self.app.post("/raclette/invite", data=
                    {"emails": 'alexis@notmyidea.org, toto@notmyidea.org'})

            # only one message is sent to multiple persons
            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0].recipients, 
                    ["alexis@notmyidea.org", "toto@notmyidea.org"])

        # mail address checking
        with run.mail.record_messages() as outbox:
            response = self.app.post("/raclette/invite", data={"emails": "toto"})
            self.assertEqual(len(outbox), 0) # no message sent
            self.assertIn("The email toto is not valid", response.data)

        # mixing good and wrong adresses shouldn't send any messages
        with run.mail.record_messages() as outbox:
            self.app.post("/raclette/invite", data=
                    {"emails": 'alexis@notmyidea.org, alexis'}) # not valid

            # only one message is sent to multiple persons
            self.assertEqual(len(outbox), 0)


    def test_project_creation(self):
        with run.app.test_client() as c:

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
        self.post_project("raclette")
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

        # adding him again should reactivate him
        self.app.post("/raclette/members/add", data={'name': 'fred' })
        self.assertEqual(
                len(models.Project.query.get("raclette").active_members), 2)

        # adding an user with the same name as another user from a different 
        # project should not cause any troubles
        self.post_project("randomid")
        self.login("randomid")
        self.app.post("/randomid/members/add", data={'name': 'fred' })
        self.assertEqual(
                len(models.Project.query.get("randomid").active_members), 1)


    def test_demo(self):
        # Test that it is possible to connect automatically by going onto /demo
        with run.app.test_client() as c:
            models.db.session.add(models.Project(id="demo", name=u"demonstration", 
                password="demo", contact_email="demo@notmyidea.org"))
            models.db.session.commit()
            c.get("/demo")

            # session is updated
            self.assertEqual(session['demo'], 'demo')

    def test_demo(self):
        # test that a demo project is created if none is defined
        self.assertEqual([], models.Project.query.all())
        self.app.get("/demo")
        self.assertTrue(models.Project.query.get("demo") is not None)

    def test_authentication(self):
        # raclette that the login / logout process works
        self.create_project("raclette")

        # try to see the project while not being authenticated should redirect 
        # to the authentication page
        resp = self.app.post("/raclette", follow_redirects=True)
        self.assertIn("Authentication", resp.data)
        
        # try to connect with wrong credentials should not work
        with run.app.test_client() as c:
            resp = c.post("/authenticate", 
                    data={'id': 'raclette', 'password': 'nope'})

            self.assertIn("Authentication", resp.data)
            self.assertNotIn('raclette', session)

        # try to connect with the right credentials should work
        with run.app.test_client() as c:
            resp = c.post("/authenticate", 
                    data={'id': 'raclette', 'password': 'raclette'})

            self.assertNotIn("Authentication", resp.data)
            self.assertIn('raclette', session)
            self.assertEqual(session['raclette'], 'raclette')

            # logout should wipe the session out
            c.get("/exit")
            self.assertNotIn('raclette', session)

    def test_manage_bills(self):
        self.post_project("raclette")

        # add two persons
        self.app.post("/raclette/members/add", data={'name': 'alexis' })
        self.app.post("/raclette/members/add", data={'name': 'fred' })

        members_ids = [m.id for m in models.Project.query.get("raclette").members]
        
        # create a bill
        self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'fromage à raclette',
            'payer': members_ids[0],
            'payed_for': members_ids,
            'amount': '25',
        })
        raclette = models.Project.query.get("raclette")
        bill = models.Bill.query.one()
        self.assertEqual(bill.amount, 25)

        # edit the bill
        resp = self.app.post("/raclette/edit/%s" % bill.id, data={
            'date': '2011-08-10',
            'what': u'fromage à raclette',
            'payer': members_ids[0],
            'payed_for': members_ids,
            'amount': '10',
        })

        bill = models.Bill.query.one()
        self.assertEqual(bill.amount, 10, "bill edition")

        # delete the bill
        self.app.get("/raclette/delete/%s" % bill.id)
        self.assertEqual(0, len(models.Bill.query.all()), "bill deletion")

        # test balance
        self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'fromage à raclette',
            'payer': members_ids[0],
            'payed_for': members_ids,
            'amount': '19',
        })

        self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'fromage à raclette',
            'payer': members_ids[1],
            'payed_for': members_ids[0],
            'amount': '20',
        })

        self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'fromage à raclette',
            'payer': members_ids[1],
            'payed_for': members_ids,
            'amount': '17',
        })

        balance = models.Project.query.get("raclette").get_balance()
        self.assertEqual(set(balance.values()), set([19.0, -19.0]))

    def test_edit_project(self):
        # A project should be editable

        self.post_project("raclette")
        new_data = {
            'name': 'Super raclette party!',
            'contact_email': 'alexis@notmyidea.org',
            'password': 'didoudida'
        }

        resp = self.app.post("/raclette/edit", data=new_data, 
                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        project = models.Project.query.get("raclette")

        for key, value in new_data.items():
            self.assertEqual(getattr(project, key), value, key)

        # Editing a project with a wrong email address should fail
        new_data['contact_email'] = 'wrong_email'

        resp = self.app.post("/raclette/edit", data=new_data,
                follow_redirects=True)
        self.assertIn("Invalid email address", resp.data)


if __name__ == "__main__":
    unittest.main()
