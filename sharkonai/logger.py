"""
SharkonAI Logger
Centralized logging system with rotating file handler.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler

from config import CONFIG


def setup_logger(name: str = "SharkonAI") -> logging.Logger:
    """Create and configure a logger instance with both console and file handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, CONFIG.LOG_LEVEL, logging.INFO))

    # Prevent duplicate handlers on re-initialization
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating file handler (5MB per file, keep 5 backups)
    try:
        file_handler = RotatingFileHandler(
            CONFIG.LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not create file handler: {e}")

    return logger


# Global logger instance
log = setup_logger()
