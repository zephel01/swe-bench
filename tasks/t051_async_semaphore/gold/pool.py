import asyncio


class LimitedPool:
    def __init__(self, limit):
        self._sem = asyncio.Semaphore(limit)
        self.active = 0
        self.max_active = 0

    async def run(self, coro_fn):
        await self._sem.acquire()
        try:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            return await coro_fn()
        finally:
            self.active -= 1
            self._sem.release()
