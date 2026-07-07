def variance(values):
    n = len(values)
    if n < 2:
        return 0.0
    mean = 0.0
    m2 = 0.0
    count = 0
    for v in values:
        count += 1
        delta = v - mean
        mean += delta / count
        m2 += delta * (v - mean)
    return m2 / (count - 1)
