from bus import EventBus


def test_all_handlers_called():
    bus = EventBus()
    seen = []
    bus.subscribe("e", lambda p: seen.append("a"))
    bus.subscribe("e", lambda p: seen.append("b"))
    bus.publish("e")
    assert sorted(seen) == ["a", "b"]


def test_priority_order():
    bus = EventBus()
    seen = []
    bus.subscribe("e", lambda p: seen.append("low"), priority=0)
    bus.subscribe("e", lambda p: seen.append("high"), priority=10)
    bus.publish("e")
    assert seen == ["high", "low"]


def test_unsubscribe_before_publish():
    bus = EventBus()
    seen = []
    tok = bus.subscribe("e", lambda p: seen.append("x"))
    bus.unsubscribe(tok)
    bus.publish("e")
    assert seen == []


def test_payload_passed():
    bus = EventBus()
    got = []
    bus.subscribe("e", lambda p: got.append(p))
    bus.publish("e", 42)
    assert got == [42]
