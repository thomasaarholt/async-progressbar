# async-progressbar

An asynchronous progress bar for Python, supporting both terminal and Jupyter notebook environments.

## Installation

```bash
pip install async-progressbar
```

## Usage

### Basic Example

```python
import asyncio
from async_progressbar import AsyncProgressBar

async def main():
    total = 100
    bar = AsyncProgressBar(total)
    for _ in range(total):
        await asyncio.sleep(0.01)
        await bar.update(1)
    await bar.finish()

asyncio.run(main())
```

### With aiolimiter (rate-limited requests)

```python
import asyncio
import random
import time
from async_progressbar import AsyncProgressBar
import aiolimiter

number_of_requests = 1000
rate_limiter = aiolimiter.AsyncLimiter(500, 1)
progressbar = AsyncProgressBar(number_of_requests)

async def request(i):
    async with rate_limiter:
        await progressbar.update(1)
        await asyncio.sleep(random.random() * 0.01)
        return i

async def main():
    await asyncio.gather(*(request(i) for i in range(number_of_requests)))
    await progressbar.finish()

if __name__ == "__main__":
    t1 = time.time()
    asyncio.run(main())
    print(f"Total time: {time.time() - t1:.2f} seconds")
```

### In Jupyter Notebooks

The progress bar will automatically use an interactive widget if run in a Jupyter notebook.

## API

- `AsyncProgressBar(total, leave=True, prefix="", suffix="", fill="█", minimum_interval=0.1)`
  - `update(progress=1)`: Increment the progress bar.
  - `draw()`: Redraw the progress bar.
  - `finish()`: Mark the progress bar as finished.
  - `reset()`: Reset the progress bar.

## Testing

To run the tests:

```bash
pytest
```
