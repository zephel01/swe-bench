import pytest

from cart import Cart


def make_cart():
    cart = Cart()
    cart.add("widget", 25.0, 2)
    cart.add("gadget", 50.0, 1)
    return cart  # subtotal 100.0


def test_save10():
    assert make_cart().total_with_discount("SAVE10") == 90.0


def test_no_code():
    assert make_cart().total_with_discount() == 100.0


def test_unknown_code():
    assert make_cart().total_with_discount("BOGUS") == 100.0


def test_half():
    assert make_cart().total_with_discount("half") == 50.0


def test_invalid_add():
    cart = Cart()
    with pytest.raises(ValueError):
        cart.add("bad", -1.0)
