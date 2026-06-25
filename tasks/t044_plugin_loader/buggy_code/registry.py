class Registry:
    def __init__(self):
        self.plugins = {}

    def register(self, name, deps=()):
        self.plugins[name] = {"deps": list(deps)}

    def deps(self, name):
        return self.plugins[name]["deps"]

    def names(self):
        return list(self.plugins)
