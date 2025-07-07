from __future__ import annotations

import random
import sys
import asyncio
from aiolimiter import AsyncLimiter
import shutil

def use_ipywidgets_progressbar() -> bool:
    try:
        from IPython.core.getipython import get_ipython
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True
        else:
            return False
    except NameError:
        return False



class TerminalProgressBar:
    _terminal_bar_count = 0

    def __init__(
        self,
        total: int,
        prefix: str = "",
        suffix: str = "",
        decimals: int = 1,
        length: int | None = None,
        fill: str = "█",
    ):
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.decimals = decimals
        if length is None:
            term_size = shutil.get_terminal_size()
            reserved = len(prefix) + len(suffix) + 10
            self.length = max(10, term_size.columns - reserved)
        else:
            self.length = length
        self.fill = fill
        self.progress = 0
        self._bar_line = TerminalProgressBar._terminal_bar_count
        TerminalProgressBar._terminal_bar_count += 1

    async def update(self, progress: int):
        self.progress += progress
        await self.draw()

    async def draw(self):
        percent = ("{0:." + str(self.decimals) + "f}").format(
            100 * (self.progress / float(self.total))
        )
        filled_length = int(self.length * self.progress // self.total)
        bar = self.fill * filled_length + "-" * (self.length - filled_length)
        if self._bar_line is not None:
            sys.stdout.write("\0337")
            sys.stdout.write(f"\033[{TerminalProgressBar._terminal_bar_count - self._bar_line}A")
            sys.stdout.write(f"\r{self.prefix} |{bar}| {percent}% {self.suffix}\033[K")
            sys.stdout.write("\0338")
            sys.stdout.flush()
        else:
            sys.stdout.write(f"\r{self.prefix} |{bar}| {percent}% {self.suffix}")
            sys.stdout.flush()

    async def finish(self):
        if self._bar_line is not None:
            sys.stdout.write(f"\033[{TerminalProgressBar._terminal_bar_count - self._bar_line}B")
        sys.stdout.write("\n")
        sys.stdout.flush()


class NotebookProgressBar:
    def __init__(
        self,
        total: int,
        prefix: str = "",
        suffix: str = "",
        decimals: int = 1,
        length: int | None = None,
    ):
        from ipywidgets import Output, FloatProgress, Label, HBox
        from IPython.display import display
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.decimals = decimals
        self.length = length if length is not None else 100
        self.progress = 0
        self.output: Output = Output()
        with self.output:
            self.output.clear_output(wait=True)
            self.progress_bar = FloatProgress(
                value=0.0,
                min=0.0,
                max=self.total,
                bar_style="info",
                layout={"width": "60%"},
            )
            self.textbox = Label(
                value=f"{self.progress_bar.value} / {self.total}",
                layout={"width": "20%", "height": "30px"},
            )
            self.widget = HBox([self.progress_bar, self.textbox])
            display(self.widget)
        display(self.output)

    async def update(self, progress: int):
        self.progress += progress
        self.progress_bar.value = self.progress
        self.textbox.value = f"{self.progress_bar.value} / {self.total}"
        await self.draw()

    async def draw(self):
        pass  # Jupyter widgets auto-update

    async def finish(self):
        pass  # Optionally update style or finalize


class AsyncProgressBar:
    """A simple async progress bar (delegates to terminal or notebook implementation)."""

    def __init__(
        self,
        total: int,
        prefix: str = "",
        suffix: str = "",
        decimals: int = 1,
        length: int | None = None,
        fill: str = "█",
    ):
        if use_ipywidgets_progressbar():
            self._impl = NotebookProgressBar(total, prefix, suffix, decimals, length)
        else:
            self._impl = TerminalProgressBar(total, prefix, suffix, decimals, length, fill)

    async def update(self, progress: int):
        await self._impl.update(progress)

    async def draw(self):
        await self._impl.draw()

    async def finish(self):
        await self._impl.finish()

if __name__ == "__main__":

    progressbar1 = AsyncProgressBar(100)
    progressbar2 = AsyncProgressBar(100)

    # Reserve lines for the two progress bars at the start (after bars are created)
    # Reserve lines for the two progress bars at the start (after bars are created)
    print("\n" * (TerminalProgressBar._terminal_bar_count))


    async def request(i: int):
        await progressbar1.update(5)
        await asyncio.sleep(3 * random.random())
        await progressbar2.update(5)


    async def main():
        requests = [request(i) for i in range(20)]
        await asyncio.gather(*requests)


    if __name__ == "__main__":
        asyncio.run(main())
