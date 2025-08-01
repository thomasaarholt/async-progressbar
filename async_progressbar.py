from __future__ import annotations

import random
import sys
import asyncio
import shutil
import time

SAVE_CURSOR_POSITION = "\0337"
RESTORE_CURSOR_POSITION = "\0338"
MOVE_CURSOR_TO_LINE_START = "\r"
CLEAR_LINE_FROM_CURSOR_TO_END = "\033[K"


def move_cursor_up_lines(n: int) -> str:
    return f"\033[{n}A"


def move_cursor_down_lines(n: int) -> str:
    return f"\033[{n}B"


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
        self.total: float = total
        self.leave: bool = leave
        self.prefix: str = prefix
        self.suffix: str = suffix
        self.progress: int = 0
        self._last_update_time: float = 0.0
        self._minimum_interval: float = minimum_interval
        self._last_update_progress: int = 0
        self._rate: float = 0.0
        self._start_time: float | None = None

    async def update(self, progress: int = 1):
        "Update the progress bar if the minimum interval time has passed."
        # Reserve lines on first update call
        if not TerminalProgressBar.lines_reserved:
            TerminalProgressBar.reserve_lines()

        self.progress += progress
        now = time.time()
        if self._start_time is None:
            self._start_time = now

        if (
            now - self._last_update_time >= self._minimum_interval
            or self.progress >= self.total
        ):
            self.update_rate(now)
            await self.draw()
            self._last_update_time = now

        if self.progress >= self.total:
            await self.finish()
    @property
    def elapsed(self) -> float:
        """Get the elapsed time in seconds since the start of the progress bar."""
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    @property
    def remaining(self) -> float:
        """Estimate the remaining time in seconds."""
        if self.progress == 0 or self._rate == 0:
            return 0.0
        remaining_items = self.total - self.progress
        return remaining_items / self._rate if self._rate > 0 else 0.0

    def update_rate(self, now: float):
        """Update the rate monitor if minimum interval has passed."""
        elapsed = now - self._last_update_time
        progress_delta = self.progress - self._last_update_progress
        self._rate = progress_delta / elapsed if elapsed > 0 else 0.0
        self._last_update_progress = self.progress

    async def draw(self) -> None:
        raise NotImplementedError

    async def finish(self) -> None:
        raise NotImplementedError

    async def reset(self) -> None:
        raise NotImplementedError

    @property
    def rate(self) -> float:
        """Get the current rate of progress updates per second."""
        return self._rate

    @staticmethod
    def format_time(seconds: float) -> str:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

class TerminalProgressBar(BaseProgressBar):
    terminal_bar_count: int = 0
    lines_reserved: bool = False

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
        self.fill: str = fill
        term_size = shutil.get_terminal_size()
        reserved = len(prefix) + len(suffix) + len(str(total)) + 40
        self.bar_length: int = max(10, term_size.columns - reserved)
        self.decimals: int = 1
        self._bar_line: int = TerminalProgressBar.terminal_bar_count
        TerminalProgressBar.terminal_bar_count += 1

    @classmethod
    def reserve_lines(cls, num_bars: int | None = None):
        """Reserve lines in the terminal for multiple progress bars."""
        if not cls.lines_reserved:
            bars_to_reserve = (
                num_bars if num_bars is not None else cls.terminal_bar_count
            )
            if bars_to_reserve > 0:
                print("\n" * bars_to_reserve, end="")
                cls.lines_reserved = True

    async def draw(self):
        filled_length = int(self.bar_length * self.progress // self.total)
        bar = self.fill * filled_length + "-" * (self.bar_length - filled_length)
        rate_str = f" ({self.rate:.2f} it/s)"
        elapsed_str = BaseProgressBar.format_time(self.elapsed)
        remaining_str = BaseProgressBar.format_time(self.remaining) if self.progress > 0 else "00:00"

        sys.stdout.write(f"{SAVE_CURSOR_POSITION}")
        sys.stdout.write(
            f"{move_cursor_up_lines(TerminalProgressBar.terminal_bar_count - self._bar_line)}"
        )
        sys.stdout.write(
            f"{MOVE_CURSOR_TO_LINE_START}{self.prefix} |{bar}| {self.progress}/{self.total} {elapsed_str}<{remaining_str} {rate_str} {self.suffix}{CLEAR_LINE_FROM_CURSOR_TO_END}"
        )
        sys.stdout.write(f"{RESTORE_CURSOR_POSITION}")
        sys.stdout.flush()

    async def finish(self):
        sys.stdout.write(
            f"{move_cursor_down_lines(TerminalProgressBar.terminal_bar_count - self._bar_line)}"
        )
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
        # We keep ipywidgets and ipython imports here to
        # allow usage of the library without them
        from ipywidgets import IntProgress, Label, HBox
        from IPython.display import display

        super().__init__(total, leave, prefix, suffix, minimum_interval)

        self.prefix_label: Label = Label(value=self.prefix)
        self.suffix_label: Label = Label(value=self.suffix)
        self.progress_bar: IntProgress = IntProgress(
            value=0,
            min=0,
            max=self.total,
        )
        self.textbox: Label = Label(
            value=f"{self.progress_bar.value} / {self.total} (0.00 it/s)",
            style={'font_family': "'Fira Code', monospace"},
        )
        self.widget: HBox = HBox([
            self.prefix_label,
            self.progress_bar,
            self.textbox,
            self.suffix_label,
        ])
        display(self.widget)

    async def draw(self):
        self.progress_bar.value = self.progress
        elapsed_str = BaseProgressBar.format_time(self.elapsed)
        remaining_str = BaseProgressBar.format_time(self.remaining) if self.progress > 0 else "00:00"
        self.textbox.value = (
            f"{self.progress_bar.value}/{self.total} {elapsed_str}<{remaining_str} ({self.rate:.2f} it/s)"
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

    _impl: NotebookProgressBar | TerminalProgressBar

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
            prefix (str): Prefix string for the progress bar. Defaults to "".
            suffix (str): Suffix string for the progress bar. Defaults to "".
            fill (str): Character to use for the filled part of the bar. Defaults to "█".
            minimum_interval (float): Minimum time interval between updates in seconds. Defaults to 0.1.
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
    import aiolimiter

    number_of_requests = 10000
    rate_limiter = aiolimiter.AsyncLimiter(3000, 1)
    progressbar1 = AsyncProgressBar(number_of_requests)
    progressbar2 = AsyncProgressBar(number_of_requests)

    async def request(i: int):
        async with rate_limiter:
            await progressbar1.update(1)
            await asyncio.sleep(random.random())
            await progressbar2.update(1)
            return i

    async def main():
        requests = [request(i) for i in range(number_of_requests)]
        await asyncio.gather(*requests)

    print("Let's test the async progressbar!")
    t1 = time.time()
    asyncio.run(main())
    print(f"Total time: {time.time() - t1:.2f} seconds")
