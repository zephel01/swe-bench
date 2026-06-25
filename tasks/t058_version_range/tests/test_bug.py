from vrange import satisfies


def test_caret():
    assert satisfies("1.5.0", "^1.2.0") is True
    assert satisfies("2.0.0", "^1.2.0") is False
    assert satisfies("1.1.0", "^1.2.0") is False


def test_tilde():
    assert satisfies("1.2.9", "~1.2.0") is True
    assert satisfies("1.3.0", "~1.2.0") is False


def test_compound_range():
    assert satisfies("1.5.0", ">=1.0.0 <2.0.0") is True
    assert satisfies("2.1.0", ">=1.0.0 <2.0.0") is False


def test_caret_zero_major():
    assert satisfies("0.2.5", "^0.2.0") is True
    assert satisfies("0.3.0", "^0.2.0") is False
