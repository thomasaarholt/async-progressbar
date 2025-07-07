import random
import sys
import asyncio
from aiolimiter import AsyncLimiter
from ipywidgets import Output, VBox, FloatProgress, Text, Label, HBox
from IPython.display import display


class AsyncProgressBar:
    """A simple async progress bar."""

    def __init__(
        self,
        total,
        prefix="",
        suffix="",
        decimals=1,
        length=100,
        fill="█",
        print_to_stdout=True,
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
            print_to_stdout (bool, optional): Whether to print to stdout. Defaults to True.
        """
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.decimals = decimals
        self.length = length
        self.fill = fill
        self.progress = 0
        self.print_to_stdout = print_to_stdout
        self.output: Output = Output()
        self.jupyter = False

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
        if self.print_to_stdout:
            percent = ("{0:." + str(self.decimals) + "f}").format(
                100 * (self.progress / float(self.total))
            )
            filled_length = int(self.length * self.progress // self.total)
            bar = self.fill * filled_length + "-" * (self.length - filled_length)
            sys.stdout.write(f"\r{self.prefix} |{bar}| {percent}% {self.suffix}")
            sys.stdout.flush()

    async def finish(self):
        """Finish the progress bar."""
        # await self.draw()
        if self.print_to_stdout:
            sys.stdout.write("\n")
            sys.stdout.flush()




async def main():
    """Example usage of the async progress bar."""
    total = 100
    # pbar = AsyncProgressBar(total, prefix="Progress:", suffix="Complete", length=50)
    rate_limiter = AsyncLimiter(5, 1)  # Limit to 1 request every 3 seconds
    progressbar1 = AsyncProgressBar(100)
    progressbar2 = AsyncProgressBar(100)
    for _ in range(total + 1):
        async with rate_limiter:
            await progressbar1.update(5)
            await asyncio.sleep(3*random.random())
            await progressbar2.update(5)
            
    await progressbar1.finish()
    await progressbar2.finish()


if __name__ == "__main__":
    asyncio.run(main())
