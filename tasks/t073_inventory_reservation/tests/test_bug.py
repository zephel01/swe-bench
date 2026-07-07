import pytest

from inventory import Inventory, InventoryError


def _check_invariants(inv):
    active = sum(r["qty"] for r in inv._res.values() if r["status"] == "active")
    confirmed = sum(r["qty"] for r in inv._res.values() if r["status"] == "confirmed")
    assert inv.reserved == active
    assert inv.available() >= 0
    return confirmed


def test_cannot_confirm_expired_reservation():
    inv = Inventory(100)
    a = inv.reserve(30, ttl=5)       # deadline at t=5
    b = inv.reserve(20, ttl=100)     # long lived
    inv.tick(10)                     # a expires here
    inv.confirm(b)                   # confirming the live reservation is fine

    # a has already expired; confirming it must be rejected.
    with pytest.raises(InventoryError):
        inv.confirm(a)

    confirmed = _check_invariants(inv)
    assert confirmed == 20           # only b was confirmed
    assert inv.on_hand == 80         # only b was deducted from stock
    assert inv.reserved == 0


def test_confirm_after_release_is_rejected():
    inv = Inventory(100)
    a = inv.reserve(40, ttl=100)
    inv.release(a)
    with pytest.raises(InventoryError):
        inv.confirm(a)               # already released
    _check_invariants(inv)
    assert inv.on_hand == 100
    assert inv.reserved == 0
