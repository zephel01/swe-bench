from scopes import REQUEST, SINGLETON, TRANSIENT


class Container:
    def __init__(self):
        self._factories = {}
        self._scopes = {}
        self._singletons = {}

    def register(self, key, factory, scope=TRANSIENT):
        self._factories[key] = factory
        self._scopes[key] = scope

    def resolve(self, key, request=None):
        scope = self._scopes[key]
        if scope == SINGLETON:
            if key not in self._singletons:
                self._singletons[key] = self._factories[key]()
            return self._singletons[key]
        if scope == REQUEST:
            if request is None:
                raise RuntimeError("request scope requires a request context")
            cache = request.setdefault("_cache", {})
            if key not in cache:
                cache[key] = self._factories[key]()
            return cache[key]
        return self._factories[key]()
