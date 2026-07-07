from inventory import Inventory


def test_reserve_and_confirm():
    inv = Inventory(100)
    r = inv.reserve(30, ttl=10)
    assert inv.available() == 70
    inv.confirm(r)
    assert inv.on_hand == 70
    assert inv.reserved == 0
    assert inv.available() == 70


def test_expired_reservation_frees_availability():
    inv = Inventory(100)
    inv.reserve(40, ttl=5)
    assert inv.available() == 60
    inv.tick(10)                 # clock passes the deadline
    assert inv.available() == 100
    # the freed capacity is reusable
    r2 = inv.reserve(80, ttl=5)
    assert inv.reserved == 80
    inv.confirm(r2)
    assert inv.on_hand == 20


def test_release_active_restores_availability():
    inv = Inventory(50)
    r = inv.reserve(20, ttl=100)
    inv.release(r)
    assert inv.available() == 50
    assert inv.reserved == 0
