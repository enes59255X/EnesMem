"""
logger.py — Structured logging configuration for EnesMem.
Single logger instance used across all modules.
"""
import logging
import sys
from pathlib import Path


LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
LOG_DATE   = "%H:%M:%S"


def setup_logger(name: str = "EnesMem", level: int = logging.DEBUG) -> logging.Logger:
    """
    Create (or retrieve) the application logger.
    Writes to stderr + an optional log file in the project root.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        # Already configured — reuse
        return logger

    logger.setLevel(level)

    # Console handler — colored prefix via level name
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE))
    logger.addHandler(ch)

    # File handler (optional, non-blocking)
    try:
        log_path = Path(__file__).parent.parent / "enes_mem.log"
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE))
        logger.addHandler(fh)
    except OSError:
        pass  # If we can't write a log file, that's fine

    return logger


# Module-level convenience instance
log = setup_logger()
