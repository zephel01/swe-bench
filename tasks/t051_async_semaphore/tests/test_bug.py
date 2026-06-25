import asyncio

from pool import LimitedPool


def test_exception_does_not_exhaust_pool():
    pool = LimitedPool(2)

    async def main():
        async def boom():
            await asyncio.sleep(0)
            raise ValueError("x")

        async def ok():
            await asyncio.sleep(0)
            return 1

        for _ in range(2):
            try:
                await pool.run(boom)
            except ValueError:
                pass
        return await asyncio.wait_for(
            asyncio.gather(*[pool.run(ok) for _ in range(3)]), timeout=2.0
        )

    assert asyncio.run(main()) == [1, 1, 1]


def test_cancellation_releases_slot():
    pool = LimitedPool(1)

    async def main():
        async def blocker():
            await asyncio.sleep(10)

        async def quick():
            await asyncio.sleep(0)
            return 1

        task = asyncio.ensure_future(pool.run(blocker))
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return await asyncio.wait_for(pool.run(quick), timeout=2.0)

    assert asyncio.run(main()) == 1


def test_limit_respected():
    pool = LimitedPool(2)

    async def main():
        async def slow():
            await asyncio.sleep(0.02)
            return 1

        await asyncio.gather(*[pool.run(slow) for _ in range(6)])
        return pool.max_active

    assert asyncio.run(main()) <= 2
