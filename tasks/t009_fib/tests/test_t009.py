from fib import fibonacci


def test_base():
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1
    assert fibonacci(2) == 1


def test_sequence():
    expected = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
    assert [fibonacci(i) for i in range(11)] == expected


def test_larger():
    assert fibonacci(30) == 832040
