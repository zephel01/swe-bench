def allocate(total_cents, weights):
    s = sum(weights)
    quotients = [(total_cents * w) // s for w in weights]
    remainders = [(total_cents * w) % s for w in weights]
    leftover = total_cents - sum(quotients)
    order = sorted(range(len(weights)), key=lambda i: remainders[i], reverse=True)
    for i in range(leftover):
        quotients[order[i]] += 1
    return quotients
