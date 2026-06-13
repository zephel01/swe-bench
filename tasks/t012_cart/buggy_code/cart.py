"""Shopping cart with discount support."""

from discounts import get_discount_rate


class Cart:
    """A shopping cart holding (name, unit_price, quantity) items."""

    def __init__(self):
        self._items = []

    def add(self, name, unit_price, quantity=1):
        """Add an item line to the cart."""
        if unit_price < 0 or quantity <= 0:
            raise ValueError("invalid price or quantity")
        self._items.append((name, unit_price, quantity))

    def subtotal(self):
        """Return the total before any discount."""
        return sum(price * qty for _, price, qty in self._items)

    def total_with_discount(self, code=None):
        """Return the total after applying the discount code."""
        rate = get_discount_rate(code)
        return round(self.subtotal() * rate, 2)
