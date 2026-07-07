from smoothing import ema


def test_empty():
    assert ema([], 0.5) == []


def test_length_preserved():
    assert len(ema([1.0, 2.0, 3.0], 0.3)) == 3


def test_converges_to_constant():
    out = ema([10.0] * 100, 0.3)
    assert abs(out[-1] - 10.0) < 1e-6
