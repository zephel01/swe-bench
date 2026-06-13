from calc import evaluate


def test_precedence():
    assert evaluate("1+2*3") == 7
    assert evaluate("2*3+4*5") == 26
    assert evaluate("2+3*4-1") == 13


def test_parentheses():
    assert evaluate("(1+2)*3") == 9
    assert evaluate("2*(3+4)") == 14


def test_left_associative():
    assert evaluate("10-2-3") == 5
    assert evaluate("8/2/2") == 2


def test_single_value():
    assert evaluate("42") == 42
