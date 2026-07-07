from recover import recover
from wal import Wal


def test_committed_transactions_apply():
    w = Wal()
    w.append(("begin", 1))
    w.append(("set", 1, "a", 10))
    w.append(("commit", 1))
    w.append(("begin", 2))
    w.append(("set", 2, "b", 20))
    w.append(("commit", 2))
    assert recover(w) == {"a": 10, "b": 20}


def test_trailing_uncommitted_transaction_discarded():
    w = Wal()
    w.append(("begin", 1))
    w.append(("set", 1, "a", 10))
    w.append(("commit", 1))
    w.append(("begin", 2))
    w.append(("set", 2, "b", 20))   # crash: tx2 never commits
    assert recover(w) == {"a": 10}


def test_torn_write_truncates_log():
    w = Wal()
    w.append(("begin", 1))
    w.append(("set", 1, "a", 10))
    w.append(("commit", 1))
    w.corrupt_last()                 # the commit record is torn
    # Without a valid commit, tx1's write is not applied.
    assert recover(w) == {}
