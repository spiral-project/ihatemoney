import os
from unittest.mock import MagicMock

from flask_testing import TestCase
from werkzeug.security import generate_password_hash

from ihatemoney import models
from ihatemoney.currency_convertor import CurrencyConverter
from ihatemoney.run import create_app, db


class BaseTestCase(TestCase):
    SECRET_KEY = "TEST SESSION"
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TESTING_SQLALCHEMY_DATABASE_URI", "sqlite://"
    )
    ENABLE_CAPTCHA = False

    def create_app(self):
        # Pass the test object as a configuration.
        return create_app(self)

    def setUp(self):
        db.create_all()
        # Add dummy data to CurrencyConverter for all tests (since it's a singleton)
        mock_data = {
            "USD": 1,
            "EUR": 0.8,
            "CAD": 1.2,
            "PLN": 4,
            CurrencyConverter.no_currency: 1,
        }
        converter = CurrencyConverter()
        converter.get_rates = MagicMock(return_value=mock_data)
        # Also add it to an attribute to make tests clearer
        self.converter = converter

    def tearDown(self):
        # clean after testing
        db.session.remove()
        db.drop_all()

    def login(self, project, password=None, test_client=None):
        password = password or project

        return self.client.post(
            "/authenticate",
            data=dict(id=project, password=password),
            follow_redirects=True,
        )

    def post_project(
        self,
        id,
        follow_redirects=True,
        default_currency="XXX",
        name=None,
        password=None,
    ):
        """Create a fake project"""
        name = name or id
        password = password or id
        # create the project
        return self.client.post(
            "/create",
            data={
                "name": name,
                "id": id,
                "password": password,
                "contact_email": f"{id}@notmyidea.org",
                "default_currency": default_currency,
            },
            follow_redirects=follow_redirects,
        )

    def import_project(self, id, data, success=True):
        resp = self.client.post(
            f"/{id}/import",
            data=data,
            # follow_redirects=True,
        )
        self.assertEqual("/{id}/edit" in str(resp.response), not success)

    def create_project(self, id, default_currency="XXX", name=None, password=None):
        name = name or str(id)
        password = password or id
        project = models.Project(
            id=id,
            name=name,
            password=generate_password_hash(password),
            contact_email=f"{id}@notmyidea.org",
            default_currency=default_currency,
        )
        models.db.session.add(project)
        models.db.session.commit()

    def get_project(self, id) -> models.Project:
        return models.Project.query.get(id)


class IhatemoneyTestCase(BaseTestCase):
    TESTING = True
    WTF_CSRF_ENABLED = False  # Simplifies the tests.

    def assertStatus(self, expected, resp, url=None):
        if url is None:
            url = resp.request.path
        return self.assertEqual(
            expected,
            resp.status_code,
            f"{url} expected {expected}, got {resp.status_code}",
        )

    def enable_admin(self, password="adminpass"):
        self.app.config["ACTIVATE_ADMIN_DASHBOARD"] = True
        self.app.config["ADMIN_PASSWORD"] = generate_password_hash(password)
        return self.client.post(
            "/admin?goto=%2Fdashboard",
            data={"admin_password": password},
            follow_redirects=True,
        )
