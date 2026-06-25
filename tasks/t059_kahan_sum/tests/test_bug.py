from fsum import total


def test_catastrophic_cancellation():
    # naive accumulation loses the small terms entirely
    assert total([1.0, 1e16, 1.0, -1e16]) == 2.0


def test_small_terms_survive_large_pair():
    values = [1e-3] * 1000 + [1e16, -1e16]
    assert abs(total(values) - 1.0) < 1e-9
