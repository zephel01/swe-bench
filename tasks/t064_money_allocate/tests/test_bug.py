from allocate import allocate


def test_thirds_conserve_total():
    result = allocate(100, [1, 1, 1])
    assert sum(result) == 100
    assert result == [34, 33, 33]


def test_sixths_conserve_total():
    result = allocate(100, [1, 1, 1, 1, 1, 1])
    assert sum(result) == 100
    assert max(result) - min(result) <= 1


def test_large_total_conserved():
    assert sum(allocate(2000, [1, 1, 1])) == 2000
