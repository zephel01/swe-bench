def ema(values, alpha):
    beta = 1.0 - alpha
    numer = 0.0
    weight = 0.0
    out = []
    for v in values:
        numer = alpha * v + beta * numer
        weight = alpha + beta * weight
        out.append(numer / weight)
    return out
