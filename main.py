from __future__ import annotations
import random
import sys
import asyncio
from aiolimiter import AsyncLimiter
import shutil
import time


def use_ipywidgets_progressbar() -> bool:
    try:
        from IPython.core.getipython import get_ipython

        shell = get_ipython().__class__.__name__
        if shell == "ZMQInteractiveShell":
            return True
        else:
            return False
    except NameError:
        return False


class BaseProgressBar:
    def __init__(
        self,
        total: int,
        leave: bool = True,
        prefix: str = "",
        suffix: str = "",
        minimum_interval: float = 0.1,
    ):
        self.total = total
        self.leave = leave
        self.prefix = prefix
        self.suffix = suffix
        self.progress = 0
        self._last_update_time = 0.0
        self._minimum_interval = minimum_interval
        self._last_update_progress = 0
        self._rate = 0.0

    async def update(self, progress: int = 1):
        "Update the progress bar if the minimum interval time has passed."
        self.progress += progress
        now = time.time()

        if (
            now - self._last_update_time >= self._minimum_interval
            or self.progress >= self.total
        ):
            self.update_rate(now)
            await self.draw()
            self._last_update_time = now

        if self.progress >= self.total:
            await self.finish()

    def update_rate(self, now: float):
        """Update the rate monitor if minimum interval has passed."""
        elapsed = now - self._last_update_time
        progress_delta = self.progress - self._last_update_progress
        self._rate = progress_delta / elapsed if elapsed > 0 else 0.0
        self._last_update_progress = self.progress

    async def draw(self):
        raise NotImplementedError

    async def finish(self):
        raise NotImplementedError

    async def reset(self):
        raise NotImplementedError

    @property
    def rate(self) -> float:
        """Get the current rate of progress updates per second."""
        return self._rate


class TerminalProgressBar(BaseProgressBar):
    _terminal_bar_count = 0

    def __init__(
        self,
        total: int,
        leave: bool = True,
        prefix: str = "",
        suffix: str = "",
        minimum_interval: float = 0.1,
        fill: str = "█",
    ):
        super().__init__(total, leave, prefix, suffix, minimum_interval)
        self.fill = fill
        term_size = shutil.get_terminal_size()
        reserved = len(prefix) + len(suffix) + 12
        self.length = max(10, term_size.columns - reserved)
        self.decimals = 1
        self._bar_line = TerminalProgressBar._terminal_bar_count
        TerminalProgressBar._terminal_bar_count += 1

    async def draw(self):
        percent = ("{0:." + str(self.decimals) + "f}").format(
            100 * (self.progress / float(self.total))
        )
        filled_length = int(self.length * self.progress // self.total)
        bar = self.fill * filled_length + "-" * (self.length - filled_length)
        rate_str = f" ({self.rate:.2f} it/s)"
        if self._bar_line is not None:
            sys.stdout.write("\0337")
            sys.stdout.write(
                f"\033[{TerminalProgressBar._terminal_bar_count - self._bar_line}A"
            )
            sys.stdout.write(
                f"\r{self.prefix} |{bar}| {percent}%{rate_str} {self.suffix}\033[K"
            )
            sys.stdout.write("\0338")
            sys.stdout.flush()
        else:
            sys.stdout.write(
                f"\r{self.prefix} |{bar}| {percent}%{rate_str} {self.suffix}"
            )
            sys.stdout.flush()

    async def finish(self):
        if self._bar_line is not None:
            sys.stdout.write(
                f"\033[{TerminalProgressBar._terminal_bar_count - self._bar_line}B"
            )
        sys.stdout.write("\n")
        sys.stdout.flush()

    async def reset(self):
        self.progress = 0
        self._last_update_time = 0.0
        self._last_update_progress = 0
        self._rate = 0.0
        await self.draw()


class NotebookProgressBar(BaseProgressBar):
    def __init__(
        self,
        total: int,
        leave: bool = True,
        prefix: str = "",
        suffix: str = "",
        minimum_interval: float = 0.01,
    ):
        from ipywidgets import FloatProgress, Label, HBox
        from IPython.display import display

        super().__init__(total, leave, prefix, suffix, minimum_interval)

        self.prefix_label: Label = Label(value=self.prefix)
        self.suffix_label: Label = Label(value=self.suffix)
        self.progress_bar: FloatProgress = FloatProgress(
            value=0,
            min=0,
            max=self.total,
            # bar_style="info",
            # layout={"width": "60%"},
        )
        self.textbox: Label = Label(
            value=f"{self.progress_bar.value} / {self.total} (0.00 it/s)",
            # layout={"width": "20%", "height": "30px"},
        )
        self.widget: HBox = HBox(
            [self.prefix_label, self.progress_bar, self.textbox, self.suffix_label]
        )
        display(self.widget)

    async def draw(self):
        self.progress_bar.value = self.progress
        self.textbox.value = (
            f"{self.progress_bar.value} / {self.total} ({self.rate:.2f} it/s)"
        )

    async def finish(self):
        if not self.leave:
            self.widget.close()

    async def reset(self):
        self.widget.open()
        self.progress = 0
        self._last_update_time = 0.0
        self._last_update_progress = 0
        self._rate = 0.0
        self.progress_bar.value = 0
        self.textbox.value = f"0 / {self.total} (0.00 it/s)"
        await self.draw()


class AsyncProgressBar:
    """
    A simple async progress bar (delegates to terminal or notebook implementation).

    This class provides a unified async progress bar interface for both terminal and Jupyter environments.
    It automatically selects the appropriate implementation based on the environment.
    """

    def __init__(
        self,
        total: int,
        leave: bool = True,
        prefix: str = "",
        suffix: str = "",
        fill: str = "█",
        minimum_interval: float = 0.1,
    ):
        """
        Initialize the AsyncProgressBar.

        Args:
            total (int): The total number of items to track.
            prefix (str, optional): Prefix string for the progress bar. Defaults to "".
            suffix (str, optional): Suffix string for the progress bar. Defaults to "".
            fill (str, optional): Character to use for the filled part of the bar. Defaults to "█".
        """
        if use_ipywidgets_progressbar():
            self._impl = NotebookProgressBar(
                total,
                leave,
                prefix,
                suffix,
                minimum_interval,
            )
        else:
            self._impl = TerminalProgressBar(
                total,
                leave,
                prefix,
                suffix,
                minimum_interval,
                fill,
            )

    async def update(self, progress: int = 1):
        """
        Update the progress bar by a given amount.

        Args:
            progress (int, optional): Amount to increment the progress. Defaults to 1.
        """
        await self._impl.update(progress)

    async def draw(self):
        """
        Redraw the progress bar (force update of the display).
        """
        await self._impl.draw()

    async def finish(self):
        """
        Mark the progress bar as finished (finalize display).
        """
        await self._impl.finish()

    async def reset(self):
        """
        Reset the progress bar to its initial state.
        """
        await self._impl.reset()


if __name__ == "__main__":
    # Reserve lines for the two progress bars at the start (after bars are created)
    number_of_requests = 1000
    rate_limiter = AsyncLimiter(300, 1)  # Limit to 1 request every 3 seconds

    progressbar1 = AsyncProgressBar(
        number_of_requests, prefix="Progress 1", suffix="Complete", minimum_interval=0.5
    )
    progressbar2 = AsyncProgressBar(
        number_of_requests, prefix="Progress 2", suffix="Complete"
    )
    print("\n" * (TerminalProgressBar._terminal_bar_count))


    async def request(i: int):
        await progressbar1.update(1)
        await asyncio.sleep(random.random())
        await progressbar2.update(1)

    async def main():
        requests = [request(i) for i in range(number_of_requests)]
        await asyncio.gather(*requests)

    if __name__ == "__main__":
        asyncio.run(main())
