import pytest

from resources import Pool
from saga import SagaRunner, Step


def _make_step(pool, name, amount):
    def action(ctx):
        pool.acquire(name, amount)
        ctx["log"].append(("do", name))

    def compensate(ctx):
        pool.release(name, amount)
        ctx["log"].append(("undo", name))

    return Step(name, action, compensate)


def test_all_steps_commit():
    pool = Pool(100)
    r = SagaRunner()
    for name, amount in [("a", 10), ("b", 20), ("c", 30)]:
        r.add(_make_step(pool, name, amount))
    ctx = {"log": []}
    r.run(ctx)
    assert pool.in_use() == 60
    assert ctx["log"] == [("do", "a"), ("do", "b"), ("do", "c")]
    assert r.comp_failures == []


def test_failure_compensates_in_reverse():
    pool = Pool(100)
    r = SagaRunner()
    r.add(_make_step(pool, "a", 10))
    r.add(_make_step(pool, "b", 20))

    def boom(ctx):
        raise RuntimeError("c failed")

    r.add(Step("c", boom, lambda ctx: None))
    ctx = {"log": []}
    with pytest.raises(RuntimeError):
        r.run(ctx)
    # a and b are compensated in reverse order; the pool is fully released.
    assert pool.in_use() == 0
    assert ctx["log"] == [("do", "a"), ("do", "b"), ("undo", "b"), ("undo", "a")]
