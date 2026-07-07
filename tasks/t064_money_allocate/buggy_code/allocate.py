def allocate(total_cents, weights):
    s = sum(weights)
    return [round(total_cents * w / s) for w in weights]
