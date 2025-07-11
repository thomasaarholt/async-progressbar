import sys
from io import StringIO
import pytest
from unittest.mock import patch, MagicMock

from async_progressbar import TerminalProgressBar, NotebookProgressBar, AsyncProgressBar, use_ipywidgets_progressbar

@pytest.fixture(autouse=True)
def reset_terminal_progress_bar_state():
    """Resets the class-level state of TerminalProgressBar before each test."""
    TerminalProgressBar.terminal_bar_count = 0
    TerminalProgressBar.lines_reserved = False

@pytest.mark.asyncio
async def test_terminal_progress_bar_creation():
    """Tests the creation of a TerminalProgressBar."""
    bar = TerminalProgressBar(total=100)
    assert bar.total == 100
    assert bar.progress == 0

@pytest.mark.asyncio
async def test_terminal_progress_bar_update_and_draw():
    """Tests that the terminal progress bar updates and draws correctly."""
    bar = TerminalProgressBar(total=100, prefix="Test:")
    
    # Redirect stdout to capture the output of the draw method
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    await bar.update(10)
    
    # Restore stdout
    sys.stdout = old_stdout
    
    output = captured_output.getvalue()
    # Check that the prefix and percentage are in the output
    assert "Test:" in output
    assert "10.0%" in output

@pytest.mark.asyncio
async def test_two_terminal_progress_bars():
    """Tests the behavior of two simultaneous terminal progress bars."""
    bar1 = TerminalProgressBar(total=100, prefix="Bar1:")
    bar2 = TerminalProgressBar(total=100, prefix="Bar2:")

    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        # Manually reserve lines to simulate the terminal environment
        # Update first bar
        await bar1.update(10)
        output1 = mock_stdout.getvalue()

        # Update second bar
        await bar2.update(20)
        output2 = mock_stdout.getvalue()

    # Check that the first bar's update moves the cursor up two lines
    from async_progressbar import move_cursor_up_lines
    assert move_cursor_up_lines(2) in output1
    assert "Bar1:" in output1
    assert "10.0%" in output1

    # Check that the second bar's update moves the cursor up one line
    assert move_cursor_up_lines(1) in output2
    assert "Bar2:" in output2
    assert "20.0%" in output2

    # 2 new lines followed by ANSI sequences followed by actual progressbars
    assert len(output2.splitlines()) == 2 + 1 + 2


@pytest.mark.asyncio
async def test_terminal_progress_bar_finish_output():
    """Tests that the output of a finished progress bar is a single newline."""
    bar = TerminalProgressBar(total=100)
    # Mock stdout to capture output
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        # Manually reserve lines to avoid initial newlines in output
        TerminalProgressBar.reserve_lines(1)
        # Reset buffer to ignore reservation output
        mock_stdout.seek(0)
        mock_stdout.truncate()

        await bar.finish()
        output = mock_stdout.getvalue()

    # The finish method should move the cursor down one line.
    # This corresponds to a single newline character if we interpret ANSI codes.
    # Or more simply, we check the raw output.
    from async_progressbar import move_cursor_down_lines
    assert output == move_cursor_down_lines(1)

@pytest.mark.asyncio
async def test_terminal_progress_bar_finish():
    """Tests that the progress bar reaches 100% when finished."""
    bar = TerminalProgressBar(total=100)
    # Mock stdout to avoid printing during tests
    with patch('sys.stdout', new_callable=StringIO):
        await bar.update(100)
    assert bar.progress >= bar.total

# Mocking ipywidgets for NotebookProgressBar tests
# This allows testing the notebook progress bar without a real Jupyter environment
class MockFloatProgress:
    def __init__(self, *args, **kwargs):
        self.value = 0
        self.max = kwargs.get('max', 100)
    def close(self):
        pass
    def open(self):
        pass

class MockLabel:
    def __init__(self, *args, **kwargs):
        self.value = ""

class MockHBox:
    def __init__(self, *args, **kwargs):
        pass
    def close(self):
        pass
    def open(self):
        pass

mock_ipywidgets = {
    'FloatProgress': MockFloatProgress,
    'Label': MockLabel,
    'HBox': MockHBox,
}

@pytest.mark.asyncio
@patch.dict('sys.modules', {'ipywidgets': MagicMock(**mock_ipywidgets), 'IPython.display': MagicMock(), 'IPython.core.getipython': MagicMock()})
async def test_notebook_progress_bar_creation():
    """Tests the creation of a NotebookProgressBar."""
    from ipywidgets import FloatProgress
    
    bar = NotebookProgressBar(total=100)
    assert bar.total == 100
    assert isinstance(bar.progress_bar, FloatProgress)

@pytest.mark.asyncio
@patch.dict('sys.modules', {'ipywidgets': MagicMock(**mock_ipywidgets), 'IPython.display': MagicMock(), 'IPython.core.getipython': MagicMock()})
async def test_notebook_progress_bar_update():
    """Tests that the notebook progress bar updates its value correctly."""
    bar = NotebookProgressBar(total=100)
    await bar.update(25)
    assert bar.progress == 25
    assert bar.progress_bar.value == 25

def test_use_ipywidgets_progressbar_in_terminal():
    """Tests that the environment check correctly identifies a terminal."""
    with patch('IPython.core.getipython.get_ipython', side_effect=NameError):
        assert not use_ipywidgets_progressbar()

def test_use_ipywidgets_progressbar_in_notebook():
    """Tests that the environment check correctly identifies a notebook."""
    mock_ipython = MagicMock()
    mock_ipython.__class__.__name__ = 'ZMQInteractiveShell'
    with patch('IPython.core.getipython.get_ipython', return_value=mock_ipython):
        assert use_ipywidgets_progressbar()

@pytest.mark.asyncio
async def test_async_progress_bar_chooses_terminal():
    """Tests that AsyncProgressBar chooses the terminal implementation."""
    with patch('async_progressbar.use_ipywidgets_progressbar', return_value=False):
        bar = AsyncProgressBar(total=100)
        assert isinstance(bar._impl, TerminalProgressBar)

@pytest.mark.asyncio
@patch.dict('sys.modules', {'ipywidgets': MagicMock(**mock_ipywidgets), 'IPython.display': MagicMock(), 'IPython.core.getipython': MagicMock()})
async def test_async_progress_bar_chooses_notebook():
    """Tests that AsyncProgressBar chooses the notebook implementation."""
    with patch('async_progressbar.use_ipywidgets_progressbar', return_value=True):
        bar = AsyncProgressBar(total=100)
        assert isinstance(bar._impl, NotebookProgressBar)
