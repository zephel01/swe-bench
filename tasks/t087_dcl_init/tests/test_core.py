from lazy import Lazy


def test_factory_runs_once_single_thread():
    calls = []

    def factory():
        calls.append(1)
        return object()

    lazy = Lazy(factory)
    first = lazy.get()
    second = lazy.get()
    assert first is second
    assert len(calls) == 1


def test_value_is_returned():
    lazy = Lazy(lambda: 123)
    assert lazy.get() == 123
    assert lazy.get() == 123
