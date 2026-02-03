from __future__ import annotations

from pathlib import Path
import os
import time

LOCK_PATH = Path("data/run.lock")


class RunLock:
    def __init__(self, timeout_seconds: int = 60 * 60):
        self.timeout_seconds = timeout_seconds

    def __enter__(self):
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)

        if LOCK_PATH.exists():
            age = time.time() - LOCK_PATH.stat().st_mtime
            if age < self.timeout_seconds:
                raise RuntimeError("Another run is already in progress (lock exists).")
            # stale lock
            LOCK_PATH.unlink(missing_ok=True)

        LOCK_PATH.write_text(str(os.getpid()), encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc, tb):
        LOCK_PATH.unlink(missing_ok=True)
