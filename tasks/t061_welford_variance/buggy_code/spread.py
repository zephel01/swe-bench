def variance(values):
    n = len(values)
    if n < 2:
        return 0.0
    total = 0.0
    total_sq = 0.0
    for v in values:
        total += v
        total_sq += v * v
    return (total_sq - total * total / n) / (n - 1)
