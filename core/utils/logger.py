"""
Security and System Event Logger for AeroSat GroundStation
"""
import logging
import sys
from pathlib import Path

# Setup logging format
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str = "AeroSat") -> logging.Logger:
    """Return configured logger instance."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # Console Handler
        c_handler = logging.StreamHandler(sys.stdout)
        c_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        c_handler.setFormatter(formatter)
        logger.addHandler(c_handler)

    return logger
