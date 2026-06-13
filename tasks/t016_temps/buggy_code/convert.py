"""Celsius/Fahrenheit conversion."""


def c_to_f(c):
    # BUG: wrong additive constant (should be 32)
    return c * 9 / 5 + 30
