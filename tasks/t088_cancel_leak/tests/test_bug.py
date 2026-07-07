import asyncio

from runner import JobRunner


def test_cancellation_releases_bookkeeping():
    runner = JobRunner()

    async def main():
        async def blocker():
            await asyncio.sleep(3600)

        task = asyncio.ensure_future(runner.run("blk", blocker()))
        # Yield until the job has entered run() and is parked at its await.
        while runner.in_use == 0:
            await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return runner.in_use, set(runner.active)

    in_use, active = asyncio.run(main())
    assert in_use == 0, f"in_use leaked after cancel: {in_use}"
    assert active == set(), f"active leaked after cancel: {active}"


def test_state_stays_consistent_after_cancel():
    runner = JobRunner()

    async def main():
        async def blocker():
            await asyncio.sleep(3600)

        async def ok():
            await asyncio.sleep(0)
            return 7

        task = asyncio.ensure_future(runner.run("blk", blocker()))
        while runner.in_use == 0:
            await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # A normal job after a cancellation must see a clean counter.
        result = await runner.run("ok", ok())
        return result, runner.in_use, set(runner.active)

    result, in_use, active = asyncio.run(main())
    assert result == 7
    assert in_use == 0, f"in_use drifted to {in_use} after cancellation"
    assert active == set()
