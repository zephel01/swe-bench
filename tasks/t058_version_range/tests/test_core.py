from vrange import satisfies


def test_exact_match():
    assert satisfies("1.2.3", "1.2.3") is True


def test_exact_no_match():
    assert satisfies("1.2.4", "1.2.3") is False
