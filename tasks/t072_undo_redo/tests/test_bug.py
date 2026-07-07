from commands import Append
from history import History


def test_new_command_after_undo_truncates_redo():
    doc = []
    h = History()
    h.apply(Append(doc, "a"))
    h.apply(Append(doc, "b"))
    h.undo()                     # doc == ["a"]; "b" is now on the redo branch
    assert doc == ["a"]

    h.apply(Append(doc, "c"))    # timeline diverges -> redo branch must be gone
    assert doc == ["a", "c"]
    assert h.can_redo() is False

    h.redo()                     # must be a no-op, not a resurrection of "b"
    assert doc == ["a", "c"]


def test_redo_branch_dropped_across_multiple_undos():
    doc = []
    h = History()
    h.apply(Append(doc, "a"))
    h.apply(Append(doc, "b"))
    h.apply(Append(doc, "c"))
    h.undo()                     # ["a", "b"]
    h.undo()                     # ["a"]
    h.apply(Append(doc, "x"))    # diverge: b and c must be unreachable
    assert doc == ["a", "x"]
    assert h.can_redo() is False
    h.redo()
    h.redo()
    assert doc == ["a", "x"]
