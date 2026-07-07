from store import KVStore


def test_savepoint_partial_rollback():
    s = KVStore()
    s.begin()
    s.set("a", 1)
    s.savepoint("sp")
    s.set("a", 2)
    s.set("b", 3)
    s.rollback_to("sp")
    assert s.get("a") == 1
    assert s.get("b") is None
    # the savepoint survives rollback_to and can be used again
    s.set("b", 9)
    s.rollback_to("sp")
    assert s.get("b") is None
    s.commit()
    assert s.get("a") == 1


def test_nested_commit_persists_on_outer_commit():
    s = KVStore()
    s.begin()
    s.set("x", "outer")
    s.begin()
    s.set("y", "inner")
    s.commit()          # inner -> outer
    s.commit()          # outer -> durable
    assert s.get("x") == "outer"
    assert s.get("y") == "inner"
    assert s.depth == 0


def test_top_level_rollback_discards():
    s = KVStore()
    s.set("keep", 1)     # no active txn -> immediate write
    s.begin()
    s.set("tmp", 2)
    s.rollback()
    assert s.get("keep") == 1
    assert s.get("tmp") is None
    assert s.depth == 0
