def ema(values, alpha):
    s = 0.0
    out = []
    for v in values:
        s = alpha * v + (1.0 - alpha) * s
        out.append(s)
    return out
