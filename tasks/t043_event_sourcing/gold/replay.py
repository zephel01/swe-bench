from projection import apply_event, empty_state
from store import Snapshot


def rebuild(store, snapshot=None):
    if snapshot is None:
        state = empty_state()
        events = store.since(0)
    else:
        state = {
            "balance": snapshot.state["balance"],
            "applied": set(snapshot.state["applied"]),
        }
        events = store.since(snapshot.offset)
    for event in events:
        state = apply_event(state, event)
    return state


def make_snapshot(store):
    state = rebuild(store)
    return Snapshot(
        {"balance": state["balance"], "applied": set(state["applied"])},
        len(store),
    )
