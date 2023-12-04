import operator
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_DOWN


class UnbalancedRequest(Exception):
    pass


def settle(balances):
    debiters, crediters = order_balance(balances)
    check_balance(debiters, crediters)
    return reduce_balance(debiters, crediters)


def check_balance(debiters, crediters):
    def _sum(balance):
        return sum([abs(v) for _, v in balance])

    sum_debiters = _sum(debiters)
    sum_crediters = _sum(crediters)

    if abs(sum_crediters - sum_debiters) >= 0.01:
        raise UnbalancedRequest(
            "Unsolvable : debiters (-{sum_debiters}) and crediters "
            "(+{sum_crediters}) are unbalanced.".format(
                sum_crediters=sum_crediters, sum_debiters=sum_debiters
            )
        )


def order_balance(balances):
    balances_dict = defaultdict(Decimal)

    for _id, balance in balances:
        balances_dict[_id] += Decimal(balance)

    crediters = list()
    debiters = list()
    for _id, balance in balances_dict.items():
        if float(balance) > 0:
            crediters.append((_id, balance))
        else:
            debiters.append((_id, balance))

    return debiters, crediters


def reduce_balance(crediters, debiters, results=None):
    if len(crediters) == 0 or len(debiters) == 0:
        return results

    if results is None:
        results = []

    crediters.sort(key=operator.itemgetter(1))
    debiters.sort(key=operator.itemgetter(1), reverse=True)

    debiter, debiter_balance = crediters.pop()
    crediter, crediter_balance = debiters.pop()

    if abs(debiter_balance) > abs(crediter_balance):
        amount = abs(crediter_balance)
    else:
        amount = abs(debiter_balance)
    new_results = results[:]
    due_amount = float(amount.quantize(Decimal(".01"), rounding=ROUND_HALF_DOWN))
    if due_amount >= 0.01:
        new_results.append((debiter, due_amount, crediter))

    new_debiter_balance = debiter_balance + amount
    if new_debiter_balance < 0:
        crediters.append((debiter, new_debiter_balance))
        crediters.sort(key=operator.itemgetter(1))

    new_crediter_balance = crediter_balance - amount
    if new_crediter_balance > 0:
        debiters.append((crediter, new_crediter_balance))
        debiters.sort(key=operator.itemgetter(1), reverse=True)

    return reduce_balance(crediters, debiters, new_results)
