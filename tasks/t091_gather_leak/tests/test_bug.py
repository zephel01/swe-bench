import asyncio

from batch import run_all

# Deterministic sibling-leak reproduction.
#
# One task raises immediately; a sibling parks on a long sleep. asyncio.gather
# propagates the failure but does NOT cancel siblings, so without extra handling
# the sibling is still pending after run_all returns. Each task records itself in
# `active` on entry and removes itself in a finally block (so a cancelled task
# leaves `active`). After the failure propagates we let the loop turn a couple of
# times and check that nothing from the batch is still active.


def test_failure_cancels_siblings():
    state = {"active": set(), "completed": set()}

    async def main():
        async def sibling():
            state["active"].add("sib")
            try:
                await asyncio.sleep(3600)
                state["completed"].add("sib")
            finally:
                state["active"].discard("sib")

        async def boomer():
            state["active"].add("boom")
            try:
                await asyncio.sleep(0)
                raise ValueError("boom")
            finally:
                state["active"].discard("boom")

        st = asyncio.ensure_future(sibling())
        bt = asyncio.ensure_future(boomer())

        raised = False
        try:
            await run_all([bt, st])
        except ValueError:
            raised = True

        # Let cancellations propagate through the event loop.
        for _ in range(5):
            await asyncio.sleep(0)

        snapshot = set(state["active"])

        # Clean up any straggler so the loop closes without warnings.
        if not st.done():
            st.cancel()
        for _ in range(5):
            await asyncio.sleep(0)

        return raised, snapshot

    raised, active = asyncio.run(main())
    assert raised, "the failure should propagate"
    assert active == set(), f"sibling left running after failure: {active}"


def test_completed_sibling_is_fine():
    # When siblings finish before the failure, there is nothing to cancel and the
    # failure still propagates.
    state = {"done": []}

    async def main():
        async def quick(name):
            await asyncio.sleep(0)
            state["done"].append(name)
            return name

        async def boomer():
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            raise ValueError("boom")

        tasks = [
            asyncio.ensure_future(quick("q")),
            asyncio.ensure_future(boomer()),
        ]
        raised = False
        try:
            await run_all(tasks)
        except ValueError:
            raised = True
        return raised, list(state["done"])

    raised, done = asyncio.run(main())
    assert raised
    assert done == ["q"]
