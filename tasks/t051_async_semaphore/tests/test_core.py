import asyncio

from pool import LimitedPool


def test_runs_normal_tasks():
    pool = LimitedPool(2)

    async def main():
        async def ok():
            await asyncio.sleep(0)
            return 1

        return await asyncio.gather(*[pool.run(ok) for _ in range(5)])

    assert asyncio.run(main()) == [1, 1, 1, 1, 1]
