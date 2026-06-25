import asyncio


class LimitedPool:
    def __init__(self, limit):
        self._sem = asyncio.Semaphore(limit)
        self.active = 0
        self.max_active = 0

    async def run(self, coro_fn):
        await self._sem.acquire()
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        result = await coro_fn()
        self.active -= 1
        self._sem.release()
        return result
