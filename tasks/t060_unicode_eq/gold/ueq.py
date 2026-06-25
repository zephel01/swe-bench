import unicodedata


def equal(a, b, fold=False):
    na = unicodedata.normalize("NFC", a)
    nb = unicodedata.normalize("NFC", b)
    if fold:
        na = na.casefold()
        nb = nb.casefold()
    return na == nb
