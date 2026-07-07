import pytest

from machine import Machine
from transitions import InvalidTransition, PaymentDeclined


def _decline(machine):
    # The payment gateway rejects before charging: no ledger change.
    raise PaymentDeclined("card declined")


def test_failed_side_effect_leaves_state_untouched():
    m = Machine()
    with pytest.raises(PaymentDeclined):
        m.fire("pay", action=_decline)

    # Payment failed, so the order must still be in "created" with no history.
    assert m.state == "created"
    assert m.history == []

    # An illegal follow-up must therefore be impossible.
    with pytest.raises(InvalidTransition):
        m.fire("ship")
    assert m.ledger == 0


def test_failed_payment_does_not_queue_phantom_refund():
    m = Machine()
    with pytest.raises(PaymentDeclined):
        m.fire("pay", action=_decline)
    # Nothing recorded, so a rewind must not refund a payment never made.
    m.rewind(1)
    assert m.ledger == 0
    assert m.state == "created"
