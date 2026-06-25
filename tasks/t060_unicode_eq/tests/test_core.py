from ueq import equal


def test_ascii_equal():
    assert equal("abc", "abc") is True


def test_ascii_not_equal():
    assert equal("abc", "abd") is False


def test_ascii_fold():
    assert equal("ABC", "abc", fold=True) is True
