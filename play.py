from typing import TypeVar
import asyncio
import random

T = TypeVar("T")

class Queue:
    def __init__(self, max_rate: float):
        self.max_rate = max_rate
        self.interval = 1 / max_rate
        self.queue = asyncio.Queue()

    async def put(self, task):
        self.queue.put(task)

    async def worker(self):
        while True:
            task = await self.queue.get()
            yield await task()
            await asyncio.sleep(self.interval)
            self.queue.task_done()


async def request():
    random_time = random.random()
    await asyncio.sleep(random_time)
    print(random_time)
    return random_time

async def main():
    queue = Queue(max_rate=1)
    requests = []
    for _ in range(10):
        queue.put(request)

    requests = [asyncio.Task(request()) for _ in range(10)]
    responses = await asyncio.gather(*requests)
    return responses

asyncio.run(main())
