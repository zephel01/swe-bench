from bus import EventBus


def test_unsubscribe_during_dispatch_skips_target():
    bus = EventBus()
    seen = []
    state = {}

    def first(_):
        seen.append("first")
        bus.unsubscribe(state["b"])   # 後続の購読を配信中に解除

    bus.subscribe("e", first, priority=10)
    state["b"] = bus.subscribe("e", lambda p: seen.append("second"), priority=5)
    bus.publish("e")
    assert seen == ["first"]          # second は解除済みなので呼ばれない
