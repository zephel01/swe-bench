class JobRunner:
    def __init__(self):
        self.in_use = 0
        self.max_in_use = 0
        self.active = set()

    async def run(self, name, coro):
        self.in_use += 1
        self.max_in_use = max(self.max_in_use, self.in_use)
        self.active.add(name)
        try:
            return await coro
        finally:
            self.in_use -= 1
            self.active.discard(name)
