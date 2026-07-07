from smoothing import ema


def test_constant_input_no_bias():
    assert ema([10.0, 10.0, 10.0, 10.0, 10.0], 0.5) == [10.0] * 5


def test_first_output_equals_first_sample():
    out = ema([7.0, 2.0, 9.0], 0.4)
    assert abs(out[0] - 7.0) < 1e-12


def test_two_sample_weighted_average():
    out = ema([1.0, 3.0], 0.5)
    assert abs(out[1] - (3.5 / 1.5)) < 1e-12
