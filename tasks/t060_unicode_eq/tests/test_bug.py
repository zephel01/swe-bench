from ueq import equal


def test_composed_vs_decomposed():
    composed = "é"        # é
    decomposed = "é"     # e + combining acute
    assert equal(composed, decomposed) is True


def test_decomposed_not_equal_other():
    assert equal("é", "e") is False


def test_unicode_casefold():
    # German sharp s folds to "ss"
    assert equal("straße", "STRASSE", fold=True) is True
