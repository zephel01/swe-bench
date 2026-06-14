import pytest

from interpreter import evaluate


def test_precedence():
    assert evaluate("2+3*4") == 14
    assert evaluate("(2+3)*4") == 20


def test_power_is_right_associative():
    assert evaluate("2**3**2") == 512        # 2**(3**2), 左結合だと 64


def test_unary_minus_below_power():
    assert evaluate("-2**2") == -4           # -(2**2)


def test_variables():
    assert evaluate("x*y+1", {"x": 3, "y": 4}) == 13


def test_division_is_float():
    assert evaluate("7/2") == 3.5


def test_errors():
    with pytest.raises(ValueError):
        evaluate("2*(3+4")
    with pytest.raises(ValueError):
        evaluate("a+1")
