import math


def solve(a, b, c):
    disc = b * b - 4.0 * a * c
    sq = math.sqrt(disc)
    x1 = (-b + sq) / (2.0 * a)
    x2 = (-b - sq) / (2.0 * a)
    return (x1, x2)
