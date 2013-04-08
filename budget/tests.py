 # -*- coding: utf-8 -*-
try:
    import unittest2 as unittest
except ImportError:
    import unittest  # NOQA

import base64
import json

from flask import session

import run
import models


class TestCase(unittest.TestCase):

    def setUp(self):
        run.app.config['TESTING'] = True

        run.app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///memory"
        run.app.config['CSRF_ENABLED'] = False  # simplify the tests
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
            self.app.post("/raclette/invite",
                          data={"emails": 'alexis@notmyidea.org'})

            self.assertEqual(len(outbox), 2)
            self.assertEqual(outbox[0].recipients, ["raclette@notmyidea.org"])
            self.assertEqual(outbox[1].recipients, ["alexis@notmyidea.org"])

        # sending a message to multiple persons
        with run.mail.record_messages() as outbox:
            self.app.post("/raclette/invite",
                data={"emails": 'alexis@notmyidea.org, toto@notmyidea.org'})

            # only one message is sent to multiple persons
            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0].recipients,
                    ["alexis@notmyidea.org", "toto@notmyidea.org"])

        # mail address checking
        with run.mail.record_messages() as outbox:
            response = self.app.post("/raclette/invite",
                                     data={"emails": "toto"})
            self.assertEqual(len(outbox), 0)  # no message sent
            self.assertIn("The email toto is not valid", response.data)

        # mixing good and wrong adresses shouldn't send any messages
        with run.mail.record_messages() as outbox:
            self.app.post("/raclette/invite",
              data={"emails": 'alexis@notmyidea.org, alexis'})  # not valid

            # only one message is sent to multiple persons
            self.assertEqual(len(outbox), 0)

    def test_password_reminder(self):
        # test that it is possible to have an email cotaining the password of a
        # project in case people forget it (and it happens!)

        self.create_project("raclette")

        with run.mail.record_messages() as outbox:
            # a nonexisting project should not send an email
            self.app.post("/password-reminder", data={"id": "unexisting"})
            self.assertEqual(len(outbox), 0)

            # a mail should be sent when a project exists
            self.app.post("/password-reminder", data={"id": "raclette"})
            self.assertEqual(len(outbox), 1)
            self.assertIn("raclette", outbox[0].body)
            self.assertIn("raclette@notmyidea.org", outbox[0].recipients)

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

            c.post("/create", data={
                'name': 'Another raclette party',
                'id': 'raclette',  # already used !
                'password': 'party',
                'contact_email': 'raclette@notmyidea.org'
            })

            # no new project added
            self.assertEqual(len(models.Project.query.all()), 1)

    def test_project_deletion(self):

        with run.app.test_client() as c:
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
        self.app.post("/raclette/members/add", data={'name': 'alexis'})
        self.assertEqual(len(models.Project.query.get("raclette").members), 1)

        # adds him twice
        result = self.app.post("/raclette/members/add",
                               data={'name': 'alexis'})

        # should not accept him
        self.assertEqual(len(models.Project.query.get("raclette").members), 1)

        # add fred
        self.app.post("/raclette/members/add", data={'name': 'fred'})
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
        self.app.post("/raclette/members/add", data={'name': 'fred'})
        fred_id = models.Project.query.get("raclette").members[-1].id

        # bound him to a bill
        result = self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'fromage à raclette',
            'payer': fred_id,
            'payed_for': [fred_id, ],
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
        self.app.post("/raclette/members/add", data={'name': 'fred'})
        self.assertEqual(
                len(models.Project.query.get("raclette").active_members), 2)

        # adding an user with the same name as another user from a different
        # project should not cause any troubles
        self.post_project("randomid")
        self.login("randomid")
        self.app.post("/randomid/members/add", data={'name': 'fred'})
        self.assertEqual(
                len(models.Project.query.get("randomid").active_members), 1)

    def test_person_model(self):
        self.post_project("raclette")
        self.login("raclette")

        # adds a member to this project
        self.app.post("/raclette/members/add", data={'name': 'alexis'})
        alexis = models.Project.query.get("raclette").members[-1]

        # should not have any bills
        self.assertFalse(alexis.has_bills())

        # bound him to a bill
        self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'fromage à raclette',
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
        self.app.post("/raclette/members/add", data={'name': 'alexis'})

        # try to remove the member using GET method
        response = self.app.get("/raclette/members/1/delete")
        self.assertEqual(response.status_code, 405)

        #delete user using POST method
        self.app.post("/raclette/members/1/delete")
        self.assertEqual(
                len(models.Project.query.get("raclette").active_members), 0)
        #try to delete an user already deleted
        self.app.post("/raclette/members/1/delete")

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
        self.app.post("/raclette/members/add", data={'name': 'alexis'})
        self.app.post("/raclette/members/add", data={'name': 'fred'})

        members_ids = [m.id for m in
                       models.Project.query.get("raclette").members]

        # create a bill
        self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'fromage à raclette',
            'payer': members_ids[0],
            'payed_for': members_ids,
            'amount': '25',
        })
        models.Project.query.get("raclette")
        bill = models.Bill.query.one()
        self.assertEqual(bill.amount, 25)

        # edit the bill
        self.app.post("/raclette/edit/%s" % bill.id, data={
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

        balance = models.Project.query.get("raclette").balance
        self.assertEqual(set(balance.values()), set([19.0, -19.0]))

        #Bill with negative amount
        self.app.post("/raclette/add", data={
            'date': '2011-08-12',
            'what': u'fromage à raclette',
            'payer': members_ids[0],
            'payed_for': members_ids,
            # bill with a negative value should be converted to a positive
            # value
            'amount': '-25'
        })
        bill = models.Bill.query.filter(models.Bill.date == '2011-08-12')[0]
        self.assertEqual(bill.amount, 25)

        #add a bill with a comma
        self.app.post("/raclette/add", data={
            'date': '2011-08-01',
            'what': u'fromage à raclette',
            'payer': members_ids[0],
            'payed_for': members_ids,
            'amount': '25,02',
        })
        bill = models.Bill.query.filter(models.Bill.date == '2011-08-01')[0]
        self.assertEqual(bill.amount, 25.02)

    def test_rounding(self):
        self.post_project("raclette")

        # add members
        self.app.post("/raclette/members/add", data={'name': 'alexis'})
        self.app.post("/raclette/members/add", data={'name': 'fred'})
        self.app.post("/raclette/members/add", data={'name': 'tata'})

        # create bills
        self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'fromage à raclette',
            'payer': 1,
            'payed_for': [1, 2, 3],
            'amount': '24.36',
        })

        self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'red wine',
            'payer': 2,
            'payed_for': [1],
            'amount': '19.12',
        })

        self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'delicatessen',
            'payer': 1,
            'payed_for': [1, 2],
            'amount': '22',
        })

        balance = models.Project.query.get("raclette").balance
        self.assertDictEqual(balance, {3: -8.12, 1: 8.12, 2: 0.0})

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

    def test_dashboard(self):
        response = self.app.get("/dashboard")
        self.assertEqual(response.status_code, 200)


class APITestCase(TestCase):
    """Tests the API"""

    def api_create(self, name, id=None, password=None, contact=None):
        id = id or name
        password = password or name
        contact = contact or "%s@notmyidea.org" % name

        return self.app.post("/api/projects", data={
            'name': name,
            'id': id,
            'password': password,
            'contact_email': contact
        })

    def api_add_member(self, project, name):
        self.app.post("/api/projects/%s/members" % project,
                data={"name": name}, headers=self.get_auth(project))

    def get_auth(self, username, password=None):
        password = password or username
        base64string = base64.encodestring(
                '%s:%s' % (username, password)).replace('\n', '')
        return {"Authorization": "Basic %s" % base64string}

    def assertStatus(self, expected, resp, url=""):

        return self.assertEqual(expected, resp.status_code,
                "%s expected %s, got %s" % (url, expected, resp.status_code))

    def test_basic_auth(self):
        # create a project
        resp = self.api_create("raclette")
        self.assertStatus(201, resp)

        # try to do something on it being unauth should return a 401
        resp = self.app.get("/api/projects/raclette")
        self.assertStatus(401, resp)

        # PUT / POST / DELETE / GET on the different resources
        # should also return a 401
        for verb in ('post',):
            for resource in ("/raclette/members", "/raclette/bills"):
                url = "/api/projects" + resource
                self.assertStatus(401, getattr(self.app, verb)(url),
                        verb + resource)

        for verb in ('get', 'delete', 'put'):
            for resource in ("/raclette", "/raclette/members/1",
                    "/raclette/bills/1"):
                url = "/api/projects" + resource

                self.assertStatus(401, getattr(self.app, verb)(url),
                        verb + resource)

    def test_project(self):
        # wrong email should return an error
        resp = self.app.post("/api/projects", data={
            'name': "raclette",
            'id': "raclette",
            'password': "raclette",
            'contact_email': "not-an-email"
        })

        self.assertTrue(400, resp.status_code)
        self.assertEqual('{"contact_email": ["Invalid email address."]}',
                         resp.data)

        # create it
        resp = self.api_create("raclette")
        self.assertTrue(201, resp.status_code)

        # create it twice should return a 400
        resp = self.api_create("raclette")

        self.assertTrue(400, resp.status_code)
        self.assertIn('id', json.loads(resp.data))

        # get information about it
        resp = self.app.get("/api/projects/raclette",
                headers=self.get_auth("raclette"))

        self.assertTrue(200, resp.status_code)
        expected = {
            "active_members": [],
            "name": "raclette",
            "contact_email": "raclette@notmyidea.org",
            "members": [],
            "password": "raclette",
            "id": "raclette",
            "balance": {},
        }
        self.assertDictEqual(json.loads(resp.data), expected)

        # edit should work
        resp = self.app.put("/api/projects/raclette", data={
            "contact_email": "yeah@notmyidea.org",
            "password": "raclette",
            "name": "The raclette party",
            }, headers=self.get_auth("raclette"))

        self.assertEqual(200, resp.status_code)

        resp = self.app.get("/api/projects/raclette",
                headers=self.get_auth("raclette"))

        self.assertEqual(200, resp.status_code)
        expected = {
            "active_members": [],
            "name": "The raclette party",
            "contact_email": "yeah@notmyidea.org",
            "members": [],
            "password": "raclette",
            "id": "raclette",
            "balance": {},
        }
        self.assertDictEqual(json.loads(resp.data), expected)

        # delete should work
        resp = self.app.delete("/api/projects/raclette",
                headers=self.get_auth("raclette"))

        self.assertEqual(200, resp.status_code)

        # get should return a 401 on an unknown resource
        resp = self.app.get("/api/projects/raclette",
                headers=self.get_auth("raclette"))
        self.assertEqual(401, resp.status_code)

    def test_member(self):
        # create a project
        self.api_create("raclette")

        # get the list of members (should be empty)
        req = self.app.get("/api/projects/raclette/members",
                headers=self.get_auth("raclette"))

        self.assertStatus(200, req)
        self.assertEqual('[]', req.data)

        # add a member
        req = self.app.post("/api/projects/raclette/members", data={
                "name": "Alexis"
            }, headers=self.get_auth("raclette"))

        # the id of the new member should be returned
        self.assertStatus(201, req)
        self.assertEqual("1", req.data)

        # the list of members should contain one member
        req = self.app.get("/api/projects/raclette/members",
                headers=self.get_auth("raclette"))

        self.assertStatus(200, req)
        self.assertEqual(len(json.loads(req.data)), 1)

        # edit this member
        req = self.app.put("/api/projects/raclette/members/1", data={
                "name": "Fred"
            }, headers=self.get_auth("raclette"))

        self.assertStatus(200, req)

        # get should return the new name
        req = self.app.get("/api/projects/raclette/members/1",
                headers=self.get_auth("raclette"))

        self.assertStatus(200, req)
        self.assertEqual("Fred", json.loads(req.data)["name"])

        # delete a member

        req = self.app.delete("/api/projects/raclette/members/1",
                headers=self.get_auth("raclette"))

        self.assertStatus(200, req)

        # the list of members should be empty
        # get the list of members (should be empty)
        req = self.app.get("/api/projects/raclette/members",
                headers=self.get_auth("raclette"))

        self.assertStatus(200, req)
        self.assertEqual('[]', req.data)

    def test_bills(self):
        # create a project
        self.api_create("raclette")

        # add members
        self.api_add_member("raclette", "alexis")
        self.api_add_member("raclette", "fred")
        self.api_add_member("raclette", "arnaud")

        # get the list of bills (should be empty)
        req = self.app.get("/api/projects/raclette/bills",
                headers=self.get_auth("raclette"))
        self.assertStatus(200, req)

        self.assertEqual("[]", req.data)

        # add a bill
        req = self.app.post("/api/projects/raclette/bills", data={
            'date': '2011-08-10',
            'what': u'fromage',
            'payer': "1",
            'payed_for': ["1", "2"],
            'amount': '25',
            }, headers=self.get_auth("raclette"))

        # should return the id
        self.assertStatus(201, req)
        self.assertEqual(req.data, "1")

        # get this bill details
        req = self.app.get("/api/projects/raclette/bills/1",
                headers=self.get_auth("raclette"))

        # compare with the added info
        self.assertStatus(200, req)
        expected = {
            "what": "fromage",
            "payer_id": 1,
            "owers": [
                {"activated": True, "id": 1, "name": "alexis"},
                {"activated": True, "id": 2, "name": "fred"}],
            "amount": 25.0,
            "date": "2011-08-10",
            "id": 1}

        self.assertDictEqual(expected, json.loads(req.data))

        # the list of bills should lenght 1
        req = self.app.get("/api/projects/raclette/bills",
                headers=self.get_auth("raclette"))
        self.assertStatus(200, req)
        self.assertEqual(1, len(json.loads(req.data)))

        # edit with errors should return an error
        req = self.app.put("/api/projects/raclette/bills/1", data={
            'date': '201111111-08-10',  # not a date
            'what': u'fromage',
            'payer': "1",
            'payed_for': ["1", "2"],
            'amount': '25',
            }, headers=self.get_auth("raclette"))

        self.assertStatus(400, req)
        self.assertEqual('{"date": ["This field is required."]}', req.data)

        # edit a bill
        req = self.app.put("/api/projects/raclette/bills/1", data={
            'date': '2011-09-10',
            'what': u'beer',
            'payer': "2",
            'payed_for': ["1", "2"],
            'amount': '25',
            }, headers=self.get_auth("raclette"))

        # check its fields
        req = self.app.get("/api/projects/raclette/bills/1",
                headers=self.get_auth("raclette"))

        expected = {
            "what": "beer",
            "payer_id": 2,
            "owers": [
                {"activated": True, "id": 1, "name": "alexis"},
                {"activated": True, "id": 2, "name": "fred"}],
            "amount": 25.0,
            "date": "2011-09-10",
            "id": 1}

        self.assertDictEqual(expected, json.loads(req.data))

        # delete a bill
        req = self.app.delete("/api/projects/raclette/bills/1",
                headers=self.get_auth("raclette"))
        self.assertStatus(200, req)

        # getting it should return a 404
        req = self.app.get("/api/projects/raclette/bills/1",
                headers=self.get_auth("raclette"))
        self.assertStatus(404, req)


if __name__ == "__main__":
    unittest.main()
