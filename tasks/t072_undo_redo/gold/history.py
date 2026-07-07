"""Undo/redo history with grouped operations and a single linear branch.

The history is a single linear timeline. Applying a new command after one or
more undos makes the timeline diverge, which must discard the outstanding redo
branch: the undone commands can never be reachable again once new work has been
done on top of the point they were undone to. Grouped commands are pushed and
popped as one unit.
"""

from commands import Group


class History:
    def __init__(self):
        self._undo = []
        self._redo = []
        self._group = None

    def apply(self, command):
        command.do()
        if self._group is not None:
            self._group.append(command)
            return
        self._undo.append(command)
        self._redo.clear()

    def begin_group(self):
        self._group = []

    def end_group(self):
        commands = self._group
        self._group = None
        if commands:
            self._undo.append(Group(commands))
            self._redo.clear()

    def undo(self):
        if not self._undo:
            return
        item = self._undo.pop()
        item.undo()
        self._redo.append(item)

    def redo(self):
        if not self._redo:
            return
        item = self._redo.pop()
        item.do()
        self._undo.append(item)

    def can_undo(self):
        return bool(self._undo)

    def can_redo(self):
        return bool(self._redo)
