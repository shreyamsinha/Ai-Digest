from __future__ import annotations

import logging
from pathlib import Path
from src.config.settings import get_settings


def setup_logging() -> None:
    s = get_settings()
    log_path = getattr(s, "log_file", "logs/run.log")

    Path(log_path).parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, s.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
