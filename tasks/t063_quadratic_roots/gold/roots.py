import math


def solve(a, b, c):
    disc = b * b - 4.0 * a * c
    sq = math.sqrt(disc)
    q = -0.5 * (b + sq) if b >= 0.0 else -0.5 * (b - sq)
    return (q / a, c / q)
