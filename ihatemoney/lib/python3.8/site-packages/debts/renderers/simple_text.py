def render(debiters, crediters, results):
    text = ""
    for (source, amount, destination) in results:
        text += f"{source} → {destination}: {round(amount, 2)}\n"
    return text
