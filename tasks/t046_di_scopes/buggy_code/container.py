from scopes import REQUEST, SINGLETON, TRANSIENT  # noqa: F401


class Container:
    def __init__(self):
        self._factories = {}
        self._scopes = {}
        self._singletons = {}

    def register(self, key, factory, scope=TRANSIENT):
        self._factories[key] = factory
        self._scopes[key] = scope

    def resolve(self, key, request=None):
        return self._factories[key]()
