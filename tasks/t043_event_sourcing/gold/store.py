class EventStore:
    def __init__(self):
        self.events = []

    def append(self, event):
        self.events.append(event)

    def since(self, offset):
        return self.events[offset:]

    def __len__(self):
        return len(self.events)


class Snapshot:
    def __init__(self, state, offset):
        self.state = state
        self.offset = offset
