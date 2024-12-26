from flask import Flask
from jinja2 import FileSystemBytecodeCache
import pytest

from ihatemoney.babel_utils import compile_catalogs
from ihatemoney.run import create_app, db


@pytest.fixture(autouse=True, scope="session")
def babel_catalogs():
    compile_catalogs()


@pytest.fixture(scope="session")
def jinja_cache_directory(tmp_path_factory):
    return tmp_path_factory.mktemp("cache")


@pytest.fixture
def app(request: pytest.FixtureRequest, jinja_cache_directory):
    """Create the Flask app with database"""
    app = create_app(request.cls)

    # Caches the jinja templates so they are compiled only once per test session
    app.jinja_env.bytecode_cache = FileSystemBytecodeCache(jinja_cache_directory)

    with app.app_context():
        db.create_all()
    request.cls.app = app

    yield app

    # clean after testing
    db.session.remove()
    db.drop_all()


@pytest.fixture
def client(app: Flask, request: pytest.FixtureRequest):
    client = app.test_client()
    request.cls.client = client

    yield client
