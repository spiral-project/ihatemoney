import traceback
import warnings

from cachetools import TTLCache, cached
import requests


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class CurrencyConverter(object, metaclass=Singleton):
    # Get exchange rates
    no_currency = "XXX"
    api_url = "https://api.exchangerate.host/latest?base=USD"

    def __init__(self):
        pass

    @cached(cache=TTLCache(maxsize=1, ttl=86400))
    def get_rates(self):
        try:
            rates = requests.get(self.api_url).json()["rates"]
        except Exception:
            warnings.warn(
                f"Call to {self.api_url} failed: {traceback.format_exc(limit=0).strip()}"
            )
            # In case of any exception, let's have an empty value
            rates = {}
        rates[self.no_currency] = 1.0
        return rates

    def get_currencies(self, with_no_currency=True):
        rates = [
            rate
            for rate in self.get_rates()
            if with_no_currency or rate != self.no_currency
        ]
        rates.sort(key=lambda rate: "" if rate == self.no_currency else rate)
        return rates

    def exchange_currency(self, amount, source_currency, dest_currency):
        if (
            source_currency == dest_currency
            or source_currency == self.no_currency
            or dest_currency == self.no_currency
        ):
            return amount

        rates = self.get_rates()
        source_rate = rates[source_currency]
        dest_rate = rates[dest_currency]
        new_amount = (float(amount) / source_rate) * dest_rate
        # round to two digits because we are dealing with money
        return round(new_amount, 2)
