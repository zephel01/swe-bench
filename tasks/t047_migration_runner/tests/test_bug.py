import pytest

from runner import Migration, Runner


def test_partial_failure_then_resume():
    log = []
    state = {"b_fail": True}

    def make(name):
        def fn():
            if name == "b" and state["b_fail"]:
                state["b_fail"] = False
                raise RuntimeError("boom")
            log.append(name)
        return fn

    r = Runner()
    r.add(Migration("a", [], make("a")))
    r.add(Migration("b", ["a"], make("b")))
    r.add(Migration("c", ["b"], make("c")))

    with pytest.raises(RuntimeError):
        r.run()
    assert log == ["a"]
    assert "c" not in r.applied

    r.run()
    assert log == ["a", "b", "c"]
    assert r.applied == {"a", "b", "c"}
