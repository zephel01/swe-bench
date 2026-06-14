from wrap import text_width, wrap


def test_fullwidth_counts_as_two():
    assert text_width("あい") == 4
    assert wrap("あい うえ お", 6) == ["あい", "うえ", "お"]


def test_ascii_wrapping():
    assert wrap("the quick brown fox", 9) == ["the quick", "brown fox"]


def test_long_word_on_its_own_line():
    assert wrap("supercalifragilistic done", 5) == ["supercalifragilistic", "done"]


def test_empty():
    assert wrap("   ", 5) == []


def test_validation():
    import pytest
    with pytest.raises(ValueError):
        wrap("x", 0)
