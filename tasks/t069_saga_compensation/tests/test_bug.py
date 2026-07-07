import pytest

from resources import Pool
from saga import SagaRunner, Step


def test_compensation_failure_does_not_strand_earlier_steps():
    pool = Pool(100)
    r = SagaRunner()

    def act(name, amt):
        def _a(ctx):
            pool.acquire(name, amt)

        return _a

    def comp_release(name, amt):
        def _c(ctx):
            pool.release(name, amt)

        return _c

    def comp_fail(ctx):
        raise RuntimeError("compensator for b unreachable")

    r.add(Step("a", act("a", 10), comp_release("a", 10)))
    r.add(Step("b", act("b", 20), comp_fail))
    r.add(Step("c", act("c", 30), comp_release("c", 30)))

    def boom(ctx):
        raise ValueError("d failed")

    r.add(Step("d", boom, lambda ctx: None))

    # The original failure (d) must surface, not the compensation error.
    with pytest.raises(ValueError):
        r.run({})

    # b leaked because its own compensation failed, but a and c MUST still be
    # released.  A stranded 'a' (in_use == 30) means recovery aborted early.
    assert pool.in_use() == 20
    assert [name for name, _ in r.comp_failures] == ["b"]
