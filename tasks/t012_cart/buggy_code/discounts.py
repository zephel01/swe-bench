"""Discount code table."""

_RATES = {
    "SAVE10": 0.10,
    "SAVE20": 0.20,
    "HALF": 0.50,
}


def get_discount_rate(code):
    """Return the discount rate (0.0-1.0) for a code, 0.0 if unknown."""
    if code is None:
        return 0.0
    return _RATES.get(code.upper(), 0.0)
