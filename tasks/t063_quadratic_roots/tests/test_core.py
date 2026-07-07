from roots import solve


def test_textbook_roots():
    assert sorted(solve(1.0, -3.0, 2.0)) == [1.0, 2.0]


def test_symmetric_roots():
    r = sorted(solve(1.0, 0.0, -4.0))
    assert abs(r[0] + 2.0) < 1e-12
    assert abs(r[1] - 2.0) < 1e-12


def test_product_small_coeffs():
    r = solve(2.0, -8.0, 6.0)
    assert abs(r[0] * r[1] - 3.0) < 1e-12
