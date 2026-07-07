from bank import Account, Bank


def test_single_thread_transfers_conserve_total():
    a = Account(0, 100)
    b = Account(1, 100)
    bank = Bank()
    assert bank.transfer(a, b, 30) is True
    assert bank.transfer(b, a, 10) is True
    assert a.balance == 80
    assert b.balance == 120
    assert a.balance + b.balance == 200


def test_insufficient_funds_rejected():
    a = Account(0, 5)
    b = Account(1, 0)
    bank = Bank()
    assert bank.transfer(a, b, 10) is False
    assert a.balance == 5
    assert b.balance == 0


def test_many_same_direction_transfers():
    a = Account(0, 1000)
    b = Account(1, 0)
    bank = Bank()
    for _ in range(500):
        bank.transfer(a, b, 1)
    assert a.balance == 500
    assert b.balance == 500
