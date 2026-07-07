"""The order-workflow transition table and its compensations.

TRANSITIONS maps a state to the events it accepts and the state each event
leads to. COMPENSATIONS maps an event to the action that reverses its effect
when a recorded transition is rewound.
"""


class InvalidTransition(Exception):
    pass


class PaymentDeclined(Exception):
    pass


TRANSITIONS = {
    "created": {"pay": "paid", "cancel": "cancelled"},
    "paid": {"ship": "shipped", "refund": "created"},
    "shipped": {"deliver": "delivered"},
}


def next_state(state, event):
    table = TRANSITIONS.get(state, {})
    if event not in table:
        raise InvalidTransition(f"{event!r} not allowed from {state!r}")
    return table[event]


def _refund(machine):
    machine.ledger -= 100


COMPENSATIONS = {
    "pay": _refund,
}
