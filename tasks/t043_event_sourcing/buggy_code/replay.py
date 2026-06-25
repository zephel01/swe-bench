from projection import apply_event, empty_state
from store import Snapshot


def rebuild(store, snapshot=None):
    if snapshot is None:
        state = empty_state()
    else:
        state = {
            "balance": snapshot.state["balance"],
            "applied": set(snapshot.state["applied"]),
        }
    for event in store.since(0):
        state = apply_event(state, event)
    return state


def make_snapshot(store):
    state = rebuild(store)
    return Snapshot(
        {"balance": state["balance"], "applied": set(state["applied"])},
        len(store),
    )
