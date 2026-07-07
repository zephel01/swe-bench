import asyncio


async def run_all(tasks):
    return await asyncio.gather(*tasks)
