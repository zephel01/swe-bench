import math


def log_sum_exp(xs):
    return math.log(sum(math.exp(x) for x in xs))
