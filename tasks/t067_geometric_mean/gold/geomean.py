import math


def geometric_mean(values):
    total = 0.0
    for v in values:
        total += math.log(v)
    return math.exp(total / len(values))
