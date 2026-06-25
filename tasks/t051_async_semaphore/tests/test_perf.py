import asyncio
import time

from pool import LimitedPool


def test_many_tasks_complete():
    pool = LimitedPool(10)

    async def main():
        async def job():
            await asyncio.sleep(0)
            return 1

        return await asyncio.gather(*[pool.run(job) for _ in range(500)])

    start = time.perf_counter()
    results = asyncio.run(main())
    assert time.perf_counter() - start < 10.0
    assert sum(results) == 500
