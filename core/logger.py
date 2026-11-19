"""Structured logging shim that writes to file and console."""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

_LOG_FILE = Path(__file__).parent.parent / "storage" / "arcadepilot.log"


def setup_logger(name: str = "arcadepilot") -> logging.Logger:
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    fh = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


log = setup_logger()
