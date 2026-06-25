def empty_state():
    return {"balance": 0, "applied": set()}


def apply_event(state, event):
    new = {"balance": state["balance"], "applied": set(state["applied"])}
    new["applied"].add(event["id"])
    if event["type"] == "deposit":
        new["balance"] += event["amount"]
    elif event["type"] == "withdraw":
        new["balance"] -= event["amount"]
    return new
