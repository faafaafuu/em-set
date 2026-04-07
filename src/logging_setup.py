from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from .config import settings


def setup_logging() -> None:
    os.makedirs(os.path.dirname(settings.LOG_PATH), exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    handler = RotatingFileHandler(settings.LOG_PATH, maxBytes=2_000_000, backupCount=3)
    handler.setFormatter(formatter)

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.addHandler(console)
