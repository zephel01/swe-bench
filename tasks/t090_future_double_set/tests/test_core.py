from cell import ResultCell


def test_first_set_wins():
    c = ResultCell()
    assert c.set("a") is True
    assert c.set("b") is False
    assert c.get() == "a"
    assert c.is_done() is True


def test_fresh_cell_not_done():
    c = ResultCell()
    assert c.is_done() is False
    assert c.get() is None


def test_many_late_sets_all_rejected():
    c = ResultCell()
    assert c.set(1) is True
    for _ in range(100):
        assert c.set(2) is False
    assert c.get() == 1
