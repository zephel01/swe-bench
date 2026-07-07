"""An order state machine with reversible transitions.

`fire` performs a transition. It validates the event against the current state,
runs the (possibly failing) side effect, and only on success records history
and advances the state. If the side effect fails, the machine must stay exactly
where it was, so that no illegal follow-up transition becomes reachable and no
phantom compensation is ever queued.

`rewind` undoes the most recent transitions, applying each event's compensation
in reverse order.
"""

from transitions import COMPENSATIONS, next_state


class Machine:
    def __init__(self):
        self.state = "created"
        self.ledger = 0
        self.history = []      # list of (event, from_state, to_state)

    def fire(self, event, action=None):
        target = next_state(self.state, event)
        if action is not None:
            action(self)
        self.history.append((event, self.state, target))
        self.state = target

    def rewind(self, steps=1):
        for _ in range(steps):
            if not self.history:
                return
            event, from_state, _to = self.history.pop()
            comp = COMPENSATIONS.get(event)
            if comp is not None:
                comp(self)
            self.state = from_state
