import csv
import traceback
import warnings
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Optional

from cachetools import TTLCache, cached
import requests


NO_CURRENCY = "XXX"
ExchangeRates = Dict[str, float]

class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ExchangeRateGetter(ABC):

    def get_rates(self) -> Optional[ExchangeRates]:
        """Method to retrieve a list of currency conversion rates.

        Returns:
            currencies: dict - key is a three-letter currency, value is float of conversion to base currency
        """
        try:
            return self._get_rates()
        except Exception:
            warnings.warn(
                f"Exchange rate getter failed - {traceback.format_exc(limit=0).strip()}"
            )

    @abstractmethod
    def _get_rates(self) -> Optional[ExchangeRates]:
        """Actual implementation of the exchange rate getter."""
        raise NotImplementedError


class ApiExchangeRate(ExchangeRateGetter):
    api_url = "https://api.exchangerate.host/latest?base=USD"

    def _get_rates(self) -> Optional[ExchangeRates]:
        return requests.get(self.api_url).json()["rates"]  # TODO not working currently probably


class UserExchangeRate(ExchangeRateGetter):
    user_csv_file = "path/to/file.csv"

    def _get_rates(self) -> Optional[ExchangeRates]:
        """Get rates from user defined csv.

        The user_csv_file should contain the currency conversions to "USD" without 1 header row
        Example:
        ```
        currency_code,fx_rate_to_USD
        CZK,25.0
        ...
        ```

        TODO: make it work bi-directionally
        TODO: document for the user where to place the file
        """
        reader = csv.reader(self.user_csv_file)

        rates = {}
        for row in reader:
            from_currency = row[0]
            rate = float(row[1])
            # TODO add validation and exception handling for typos
            rates[from_currency] = rate
        return rates


class HardCodedExchangeRate(ExchangeRateGetter):

    def _get_rates(self) -> Optional[dict]:
        return {"USD": 1.0}  # TODO fill in more


class CurrencyConverter(object, metaclass=Singleton):
    no_currency = NO_CURRENCY

    def __init__(self):
        pass

    @cached(cache=TTLCache(maxsize=1, ttl=86400))
    def get_rates(self):
        """Try to retrieve the exchange rate from various sources, defaulting to hard coded values."""
        for provider in [ApiExchangeRate, UserExchangeRate, HardCodedExchangeRate]:
            if rates:= provider.get_rates():
                break
        else:
            rates = {}
        rates[NO_CURRENCY] = 1.0
        return rates

    def get_currencies(self, with_no_currency: bool=True) -> list:
        currencies = list(self.get_rates.keys())
        if with_no_currency:
            currencies.append(self.no_currency)
        return currencies

    def exchange_currency(self, amount: float, source_currency: str, dest_currency: str) -> float:
        """Return the money amount converted from source_currency to dest_currency."""
        if (
            source_currency == dest_currency
            or source_currency == self.no_currency
            or dest_currency == self.no_currency
        ):
            return amount

        rates = self.get_rates()
        source_rate = rates[source_currency]
        dest_rate = rates[dest_currency]
        # Using Decimal to not introduce floating-point operation absolute errors
        new_amount = (Decimal(amount) / Decimal(source_rate)) * Decimal(dest_rate)
        # dealing with money - only round the shown amount before showing it to user
        # - think about 10 * 0.0003 == 0?
        return float(new_amount)
