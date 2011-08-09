import os
import tempfile
import unittest

from flask import g

import web
import models

class BudgetTestCase(unittest.TestCase):

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
        project = models.Project(id=name, name=unicode(name), password=name, 
                contact_email="%s@notmyidea.org" % name)
        models.db.session.add(project)
        models.db.session.commit()

        return project

    def test_notifications(self):
        """Test that the notifications are sent, and that email adresses
        are checked properly.
        """
        # create a project
        self.create_project("raclette")

        self.login("raclette")

        # sending a message to one person
        with web.mail.record_messages() as outbox:
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


if __name__ == "__main__":
    unittest.main()
