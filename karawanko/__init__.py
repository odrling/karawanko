import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

__version__ = "1.0.0"

console = Console(file=sys.stderr)

FORMAT = "%(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler(console=console)],
)
