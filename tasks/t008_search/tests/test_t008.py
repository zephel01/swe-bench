from search import binary_search


def test_missing_middle():
    assert binary_search([1, 3, 5], 2) == -1


def test_missing_ends():
    assert binary_search([1, 3, 5], 0) == -1
    assert binary_search([1, 3, 5], 9) == -1


def test_found():
    items = [1, 3, 5, 7, 9, 11]
    for i, v in enumerate(items):
        assert binary_search(items, v) == i


def test_empty():
    assert binary_search([], 1) == -1
