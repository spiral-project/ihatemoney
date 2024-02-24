import os

import pytest

from ihatemoney import models
from ihatemoney.utils import generate_password_hash


@pytest.mark.usefixtures("client", "converter")
class BaseTestCase:
    SECRET_KEY = "TEST SESSION"
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TESTING_SQLALCHEMY_DATABASE_URI", "sqlite://"
    )
    ENABLE_CAPTCHA = False
    PASSWORD_HASH_METHOD = "pbkdf2:sha1:1"
    PASSWORD_HASH_SALT_LENGTH = 1

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
        project_history=True,
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
                "project_history": project_history,
            },
            follow_redirects=follow_redirects,
        )

    def import_project(self, id, data, success=True):
        resp = self.client.post(
            f"/{id}/import",
            data=data,
            # follow_redirects=True,
        )
        assert ("/{id}/edit" in str(resp.response)) == (not success)

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
        assert (
            expected == resp.status_code
        ), f"{url} expected {expected}, got {resp.status_code}"

    def enable_admin(self, password="adminpass"):
        self.app.config["ACTIVATE_ADMIN_DASHBOARD"] = True
        self.app.config["ADMIN_PASSWORD"] = generate_password_hash(password)
        return self.client.post(
            "/admin?goto=%2Fdashboard",
            data={"admin_password": password},
            follow_redirects=True,
        )
