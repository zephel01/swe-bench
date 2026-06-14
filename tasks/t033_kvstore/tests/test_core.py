from store import KVStore


def test_basic_set_get_delete():
    s = KVStore()
    s.set("a", 1)
    assert s.get("a") == 1
    s.delete("a")
    assert s.get("a") is None


def test_single_commit_persists():
    s = KVStore()
    s.begin()
    s.set("a", 1)
    s.commit()
    assert s.get("a") == 1


def test_single_rollback_reverts():
    s = KVStore()
    s.set("a", 1)
    s.begin()
    s.set("a", 2)
    s.set("b", 9)
    s.rollback()
    assert s.get("a") == 1
    assert s.get("b") is None


def test_inner_rollback_only():
    s = KVStore()
    s.begin()
    s.set("a", 1)
    s.begin()
    s.set("a", 2)
    s.rollback()        # 内側だけ巻き戻す
    assert s.get("a") == 1
    s.commit()
    assert s.get("a") == 1
