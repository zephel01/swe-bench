from recover import recover
from wal import Wal


def test_interleaved_uncommitted_transaction_not_applied():
    w = Wal()
    w.append(("begin", 1))
    w.append(("set", 1, "x", 1))
    w.append(("begin", 2))
    w.append(("set", 2, "y", 2))
    w.append(("commit", 2))          # only tx2 commits
    w.append(("set", 1, "x", 99))    # tx1 keeps writing, then the process dies
    state = recover(w)
    # tx1 never committed; its writes must not appear, even though tx2 (which
    # was interleaved with it) committed in the middle.
    assert state == {"y": 2}
    assert "x" not in state


def test_two_uncommitted_around_one_commit():
    w = Wal()
    w.append(("begin", 1))
    w.append(("set", 1, "a", 1))
    w.append(("begin", 2))
    w.append(("set", 2, "b", 2))
    w.append(("begin", 3))
    w.append(("set", 3, "c", 3))
    w.append(("commit", 2))          # only tx2 commits; tx1 and tx3 crash
    w.append(("set", 1, "a", 11))
    w.append(("set", 3, "c", 33))
    assert recover(w) == {"b": 2}
