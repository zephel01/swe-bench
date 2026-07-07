"""Reversible commands and grouped commands for an undo/redo history.

A command knows how to apply itself (`do`) and to reverse itself (`undo`).
A Group bundles several commands so they behave as a single unit: `do` replays
the children in order, `undo` reverses them in the opposite order.
"""


class Append:
    def __init__(self, doc, value):
        self.doc = doc
        self.value = value

    def do(self):
        self.doc.append(self.value)

    def undo(self):
        self.doc.pop()


class Group:
    def __init__(self, commands):
        self.commands = list(commands)

    def do(self):
        for cmd in self.commands:
            cmd.do()

    def undo(self):
        for cmd in reversed(self.commands):
            cmd.undo()
