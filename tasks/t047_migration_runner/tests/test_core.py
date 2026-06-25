from runner import Migration, Runner


def test_all_succeed_in_dependency_order():
    log = []
    r = Runner()
    r.add(Migration("a", [], lambda: log.append("a")))
    r.add(Migration("b", ["a"], lambda: log.append("b")))
    r.add(Migration("c", ["b"], lambda: log.append("c")))
    applied = r.run()
    assert log == ["a", "b", "c"]
    assert applied == ["a", "b", "c"]
