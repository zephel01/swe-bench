from store import KVStore


def test_parent_rollback_undoes_committed_child():
    s = KVStore()
    s.begin()                 # parent transaction
    s.set("a", "A")
    s.begin()                 # child transaction
    s.set("b", "B")           # key touched only inside the child
    s.set("a", "A2")          # child also overwrites a
    s.commit()                # child commits INTO the parent (not durable yet)
    assert s.get("b") == "B"
    assert s.get("a") == "A2"

    s.rollback()              # parent rolls back everything since parent begin
    # Everything the committed child did must be undone as well.
    assert s.get("a") is None
    assert s.get("b") is None
    assert s.depth == 0


def test_deep_nested_commit_then_middle_rollback():
    s = KVStore()
    s.begin()                 # L1
    s.set("root", 0)
    s.begin()                 # L2
    s.set("mid", 1)
    s.begin()                 # L3
    s.set("leaf", 2)
    s.commit()                # L3 -> L2
    s.commit()                # L2 -> L1
    assert s.get("leaf") == 2
    s.rollback()              # L1 discards root, mid AND leaf
    assert s.get("root") is None
    assert s.get("mid") is None
    assert s.get("leaf") is None
