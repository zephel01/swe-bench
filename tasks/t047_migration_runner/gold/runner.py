from graph import toposort


class Migration:
    def __init__(self, name, deps, fn):
        self.name = name
        self.deps = list(deps)
        self.fn = fn


class Runner:
    def __init__(self):
        self.migrations = {}
        self.applied = set()

    def add(self, migration):
        self.migrations[migration.name] = migration

    def run(self):
        nodes = list(self.migrations)
        edges = {n: self.migrations[n].deps for n in nodes}
        for name in toposort(nodes, edges):
            if name in self.applied:
                continue
            self.migrations[name].fn()
            self.applied.add(name)
        return sorted(self.applied)
