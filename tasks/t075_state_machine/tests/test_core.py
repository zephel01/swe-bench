import pytest

from machine import Machine
from transitions import InvalidTransition


def _pay(machine):
    machine.ledger += 100


def test_happy_path_and_rewind():
    m = Machine()
    m.fire("pay", action=_pay)
    assert m.state == "paid"
    assert m.ledger == 100
    m.fire("ship")
    assert m.state == "shipped"
    m.rewind(2)              # undo ship, then pay
    assert m.state == "created"
    assert m.ledger == 0     # pay was compensated (refunded)
    assert m.history == []


def test_invalid_transition_rejected():
    m = Machine()
    with pytest.raises(InvalidTransition):
        m.fire("ship")       # cannot ship before paying
    assert m.state == "created"
    assert m.history == []
