import argparse

from .solver import order_balance, check_balance, reduce_balance
from .renderers import RENDERERS
from .parsers import PARSERS


def main():
    parser = argparse.ArgumentParser(description="Settle debts.")
    parser.add_argument(
        "--settle",
        dest="settle",
        help="the identifiers and amounts to be solved"
        ' (ex. --settle "alice +200, marc -100, henri -100")',
        required=True,
    )
    parser.add_argument(
        "--parser", dest="parser", default="inline", choices=PARSERS.keys()
    )

    parser.add_argument(
        "--renderer", dest="renderer", default="simple_text", choices=RENDERERS.keys()
    )
    args = parser.parse_args()
    try:
        parser = PARSERS[args.parser]
        renderer = RENDERERS[args.renderer]

        balance = parser(args.settle)
        debiters, crediters = order_balance(balance)
        check_balance(debiters, crediters)
        results = reduce_balance(debiters[:], crediters[:])
        print(renderer.render(debiters, crediters, results))
    except Exception as e:
        print(f"Sorry, an error occured. {e}")
        raise e
