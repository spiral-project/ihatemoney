from unittest.mock import MagicMock

from flask import Flask
import pytest

from ihatemoney.currency_convertor import CurrencyConverter
from ihatemoney.run import create_app, db


@pytest.fixture
def app(request: pytest.FixtureRequest):
    """Create the Flask app with database"""
    app = create_app(request.cls)

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


@pytest.fixture
def app_ctx(app):
    """
    This fixture add both app_context AND request context for ease of use.
    If you only need an app_context locally, use `with self.app.app_context():`
    in your code.
    """
    with app.app_context(), app.test_request_context():
        yield


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
