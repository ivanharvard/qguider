# Used by cli.py. Not an example.

from collections import deque
import logging

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
)


def make_rich_ui(log_level: str = "INFO"):
    console = Console()
    log_lines = deque(maxlen=20)

    progress = Progress(
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeRemainingColumn(),
    )

    layout = Layout()
    layout.split_column(
        Layout(Panel(progress), name="progress", size=3),
        Layout(Panel("", title="Logs"), name="logs"),
    )

    class PanelLogHandler(logging.Handler):
        def emit(self, record):
            log_lines.append(self.format(record))
            layout["logs"].update(
                Panel("\n".join(log_lines), title="Logs")
            )

    handler = PanelLogHandler()
    handler.setFormatter(
        logging.Formatter("%(levelname)s:%(name)s:%(message)s")
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    return console, layout, progress, Live