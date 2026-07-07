from pool import ResourcePool


def test_single_thread_allocate_release():
    pool = ResourcePool([10, 11, 12])
    a = pool.allocate()
    b = pool.allocate()
    assert a == 10 and b == 11
    pool.release(a)
    c = pool.allocate()
    d = pool.allocate()
    assert {c, d} == {10, 12}


def test_exhaustion_returns_none():
    pool = ResourcePool([1])
    assert pool.allocate() == 1
    assert pool.allocate() is None


def test_release_makes_available_again():
    pool = ResourcePool([5])
    x = pool.allocate()
    assert x == 5
    assert pool.allocate() is None
    pool.release(5)
    assert pool.allocate() == 5
