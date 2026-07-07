"""An inventory with time-limited reservations.

Invariants that must always hold:
    reserved   == sum(qty for every reservation whose status is "active")
    available()== on_hand - reserved   (and never negative)
    on_hand    == initial_on_hand - sum(qty for every "confirmed" reservation)

A reservation is created active with an expiry deadline. It may be confirmed
(turning into a permanent deduction from on_hand) or released, and it expires
automatically once the clock passes its deadline. A reservation that is no
longer active must not be confirmable.
"""


class InventoryError(Exception):
    pass


class Inventory:
    def __init__(self, on_hand):
        self.on_hand = on_hand
        self.reserved = 0
        self.now = 0
        self._next_id = 1
        self._res = {}      # id -> {"qty", "expires", "status"}

    def available(self):
        return self.on_hand - self.reserved

    def tick(self, dt=1):
        self.now += dt
        self._expire_due()

    def _expire_due(self):
        for r in self._res.values():
            if r["status"] == "active" and r["expires"] <= self.now:
                r["status"] = "expired"
                self.reserved -= r["qty"]

    def reserve(self, qty, ttl):
        if qty <= 0:
            raise InventoryError("qty must be positive")
        self._expire_due()
        if qty > self.available():
            raise InventoryError("insufficient availability")
        rid = self._next_id
        self._next_id += 1
        self._res[rid] = {"qty": qty, "expires": self.now + ttl, "status": "active"}
        self.reserved += qty
        return rid

    def confirm(self, rid):
        self._expire_due()
        r = self._res[rid]
        if r["status"] != "active":
            raise InventoryError(f"cannot confirm {r['status']} reservation")
        r["status"] = "confirmed"
        self.reserved -= r["qty"]
        self.on_hand -= r["qty"]

    def release(self, rid):
        r = self._res[rid]
        if r["status"] == "active":
            r["status"] = "released"
            self.reserved -= r["qty"]
