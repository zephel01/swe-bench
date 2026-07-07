import asyncio

from batch import run_all


def test_all_success_returns_in_order():
    async def main():
        async def job(x):
            await asyncio.sleep(0)
            return x * 10

        tasks = [asyncio.ensure_future(job(i)) for i in range(4)]
        return await run_all(tasks)

    assert asyncio.run(main()) == [0, 10, 20, 30]


def test_single_task_result():
    async def main():
        async def job():
            await asyncio.sleep(0)
            return "ok"

        return await run_all([asyncio.ensure_future(job())])

    assert asyncio.run(main()) == ["ok"]
