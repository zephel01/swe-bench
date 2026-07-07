from roots import solve


def test_product_of_roots_large_b():
    r = solve(1.0, 1e10, 1.0)
    # product of the roots must equal c / a = 1.0
    assert abs(r[0] * r[1] - 1.0) < 1e-6


def test_small_root_survives():
    r = solve(1.0, 1e8, 1.0)
    small = min(r, key=abs)
    assert abs(small - (-1e-8)) < 1e-12
