def equal(a, b, fold=False):
    if fold:
        return a.lower() == b.lower()
    return a == b
