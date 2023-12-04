from collections import defaultdict

from jinja2 import Environment, PackageLoader, select_autoescape

env = Environment(
    loader=PackageLoader("debts", "templates"), autoescape=select_autoescape(["debts"])
)


def render(debiters, crediters, results):
    template = env.get_template("settlement.html")
    dict_results = defaultdict(lambda: defaultdict(float))
    for deb, amount, cred in results:
        dict_results[deb][cred] = amount

    rendered_html = template.render(
        debiters=debiters, crediters=crediters, results=dict_results
    )
    return rendered_html
