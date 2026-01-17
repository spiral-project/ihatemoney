from unittest.mock import MagicMock

from flask import Flask
from jinja2 import FileSystemBytecodeCache
import pytest

from ihatemoney.babel_utils import compile_catalogs
from ihatemoney.currency_convertor import CurrencyConverter
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
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app: Flask, request: pytest.FixtureRequest):
    client = app.test_client()
    request.cls.client = client

    yield client


@pytest.fixture
def converter(request: pytest.FixtureRequest):
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
    request.cls.converter = converter

    yield converter
