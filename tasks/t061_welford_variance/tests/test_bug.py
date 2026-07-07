from spread import variance


def test_large_offset_preserves_spread():
    base = [1.0, 2.0, 3.0, 4.0, 5.0]
    shifted = [x + 1e9 for x in base]
    assert abs(variance(shifted) - 2.5) < 1e-6


def test_constant_offset_variance():
    vals = [1e8 + d for d in (0.0, 0.5, 1.0)]
    # true sample variance is 0.25; naive one-pass returns garbage
    assert abs(variance(vals) - 0.25) < 1e-6
