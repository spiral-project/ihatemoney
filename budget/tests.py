import os
import tempfile
import unittest

from flask import session

import web
import models

class TestCase(unittest.TestCase):

    def setUp(self):
        web.app.config['TESTING'] = True

        self.fd, self.fp = tempfile.mkstemp()
        web.app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///%s" % self.fp
        web.app.config['CSRF_ENABLED'] = False # simplify the tests
        self.app = web.app.test_client()

        models.db.init_app(web.app)
        web.mail.init_app(web.app)

        models.db.app = web.app
        models.db.create_all()

    def tearDown(self):
        # clean after testing
        os.close(self.fd)
        os.unlink(self.fp)

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

    def test_add_member(self):
        self.create_project("raclette")
        self.login("raclette")

        # adds a member to this project
        self.app.post("/raclette/members/add", data={'name': 'alexis' })
        self.assertEqual(len(models.Project.query.get("raclette").members), 1)

        # adds him twice
        result = self.app.post("/raclette/members/add", data={'name': 'alexis' })
        # should not accept him
        self.assertEqual(len(models.Project.query.get("raclette").members), 1)


if __name__ == "__main__":
    unittest.main()
