import math


def integral(n):
    if n == 0:
        return 1.0 - 1.0 / math.e
    upper = n + 30
    e = 0.0
    for k in range(upper, n, -1):
        e = (1.0 - e) / k
    return e
