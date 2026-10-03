"""
Structured logger for GAIA Agent.
Uses Python's built-in logging with a clean, consistent format.
Never logs API keys or sensitive document contents.
"""

import logging
import sys
from datetime import datetime


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for the given module name."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        # Use UTF-8 on Windows to prevent cp1252 encode errors for Unicode chars
        stream = open(sys.stdout.fileno(), mode="w", encoding="utf-8",
                      errors="replace", buffering=1, closefd=False) \
                 if hasattr(sys.stdout, "fileno") else sys.stdout
        handler = logging.StreamHandler(stream)
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    return logger
