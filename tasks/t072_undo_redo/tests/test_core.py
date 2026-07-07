from commands import Append
from history import History


def test_linear_undo_redo():
    doc = []
    h = History()
    h.apply(Append(doc, "a"))
    h.apply(Append(doc, "b"))
    assert doc == ["a", "b"]
    h.undo()
    assert doc == ["a"]
    h.redo()
    assert doc == ["a", "b"]
    h.undo()
    h.undo()
    assert doc == []
    assert h.can_undo() is False


def test_group_is_atomic_unit():
    doc = []
    h = History()
    h.apply(Append(doc, "a"))
    h.begin_group()
    h.apply(Append(doc, "b"))
    h.apply(Append(doc, "c"))
    h.end_group()
    assert doc == ["a", "b", "c"]
    h.undo()                 # the whole group is undone at once
    assert doc == ["a"]
    h.redo()                 # and redone at once
    assert doc == ["a", "b", "c"]
