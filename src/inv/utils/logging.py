"""Logging and console feedback helper."""

import logging
import sys

from rich.console import Console

console = Console(highlight=False)
error_console = Console(stderr=True, highlight=False)

logger = logging.getLogger("inv")


def setup_logging(verbose: bool = False) -> None:
    """Configure inv logger."""
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)
    formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)

    logger.setLevel(level)
    if not logger.handlers:
        logger.addHandler(handler)

