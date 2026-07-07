import asyncio

from runner import JobRunner


def test_normal_completion_accounts_correctly():
    runner = JobRunner()

    async def main():
        async def job(x):
            await asyncio.sleep(0)
            return x * 2

        r = await runner.run("j", job(21))
        return r

    assert asyncio.run(main()) == 42
    assert runner.in_use == 0
    assert runner.active == set()


def test_exception_still_releases():
    runner = JobRunner()

    async def main():
        async def boom():
            await asyncio.sleep(0)
            raise ValueError("x")

        try:
            await runner.run("j", boom())
        except ValueError:
            pass

    asyncio.run(main())
    assert runner.in_use == 0
    assert runner.active == set()
