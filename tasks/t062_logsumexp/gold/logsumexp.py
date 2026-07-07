import math


def log_sum_exp(xs):
    if not xs:
        return float("-inf")
    m = max(xs)
    if m == float("-inf"):
        return float("-inf")
    acc = 0.0
    for x in xs:
        acc += math.exp(x - m)
    return m + math.log(acc)
