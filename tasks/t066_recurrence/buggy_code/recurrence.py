import math


def integral(n):
    e = 1.0 - 1.0 / math.e
    for k in range(1, n + 1):
        e = 1.0 - k * e
    return e
