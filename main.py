from __future__ import annotations

import random
import sys
import asyncio
from aiolimiter import AsyncLimiter
from ipywidgets import Output, FloatProgress, Label, HBox
from IPython.display import display
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


class AsyncProgressBar:
    """A simple async progress bar."""

    _terminal_bar_count = 0  # class variable to track number of vertical bars

    def __init__(
        self,
        total: int,
        prefix: str = "",
        suffix: str = "",
        decimals: int = 1,
        length: int | None = None,
        fill: str = "█",
    ):
        """
        Initialize the progress bar.

        Args:
            total (int): The total number of items.
            prefix (str, optional): The prefix string. Defaults to ''.
            suffix (str, optional): The suffix string. Defaults to ''.
            decimals (int, optional): The number of decimals for the percentage. Defaults to 1.
            length (int, optional): The character length of the bar. Defaults to 100.
            fill (str, optional): The bar fill character. Defaults to '█'.
        """
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.decimals = decimals
        self.jupyter = use_ipywidgets_progressbar()
        # Determine terminal width if not provided
        if length is None and not self.jupyter:
            term_size = shutil.get_terminal_size()
            # Reserve space for prefix, suffix, percent, and bar delimiters
            reserved = len(prefix) + len(suffix) + 10  # 10 for percent and delimiters
            self.length = max(10, term_size.columns - reserved)
        else:
            self.length = length if length is not None else 100
        self.fill = fill
        self.progress = 0
        self.output: Output = Output()

        # For terminal multi-bar support
        if not self.jupyter:
            self._bar_line = AsyncProgressBar._terminal_bar_count
            AsyncProgressBar._terminal_bar_count += 1
        else:
            self._bar_line = None

        self.output = Output()
        if self.jupyter:
            with self.output:
                self.output.clear_output(wait=True)
                self.progress_bar: FloatProgress = FloatProgress(
                    value=0.0,
                    min=0.0,
                    max=self.total,
                    bar_style="info",
                    layout={"width": "60%"},
                )
                self.textbox: Label = Label(
                    value=f"{self.progress_bar.value} / {self.total}",
                    layout={"width": "20%", "height": "30px"},
                )
                self.widget: HBox = HBox([self.progress_bar, self.textbox])
                display(self.widget)
            display(self.output)

    async def update(self, progress: int):
        """Update the progress bar."""
        self.progress += progress
        if self.jupyter:
            self.progress_bar.value = self.progress
            self.textbox.value = f"{self.progress_bar.value} / {self.total}"
        await self.draw()

    async def draw(self):
        """Draw the progress bar."""
        if not self.jupyter:
            percent = ("{0:." + str(self.decimals) + "f}").format(
                100 * (self.progress / float(self.total))
            )
            filled_length = int(self.length * self.progress // self.total)
            bar = self.fill * filled_length + "-" * (self.length - filled_length)
            if self._bar_line is not None:
                # Move cursor up to the correct line, print, then move back down
                sys.stdout.write("\0337")  # Save cursor
                sys.stdout.write(
                    f"\033[{AsyncProgressBar._terminal_bar_count - self._bar_line}A"
                )  # Move up
                sys.stdout.write(
                    f"\r{self.prefix} |{bar}| {percent}% {self.suffix}\033[K"
                )  # No newline here
                sys.stdout.write("\0338")  # Restore cursor
                sys.stdout.flush()
            else:
                sys.stdout.write(f"\r{self.prefix} |{bar}| {percent}% {self.suffix}")
                sys.stdout.flush()

    async def finish(self):
        """Finish the progress bar."""
        if not self.jupyter:
            if self._bar_line is not None:
                # After all bars are done, move cursor to the bottom
                sys.stdout.write(
                    f"\033[{AsyncProgressBar._terminal_bar_count - self._bar_line}B"
                )
            sys.stdout.write("\n")
            sys.stdout.flush()


rate_limiter = AsyncLimiter(5, 1)  # Limit to 1 request every 3 seconds

progressbar1 = AsyncProgressBar(100)
progressbar2 = AsyncProgressBar(100)

# Reserve lines for the two progress bars at the start (after bars are created)
print("\n" * (AsyncProgressBar._terminal_bar_count))


async def request(i: int):
    async with rate_limiter:
        await progressbar1.update(5)
        await asyncio.sleep(3 * random.random())
        await progressbar2.update(5)


async def main():
    requests = [request(i) for i in range(20)]
    await asyncio.gather(*requests)


if __name__ == "__main__":
    asyncio.run(main())
