"""Encoding-safe console and run-log output helpers."""

import datetime
import sys
from pathlib import Path


def print_console_safe(*values, sep=" ", end="\n", stream=None, flush=False):
    destination = stream or sys.stdout
    encoding = getattr(destination, "encoding", None) or "utf-8"
    message = sep.join(str(value) for value in values) + end
    safe_message = message.encode(encoding, errors="replace").decode(encoding)
    destination.write(safe_message)
    if flush:
        destination.flush()


def append_timestamped_line(path, message, timestamp=None):
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    recorded_at = timestamp or datetime.datetime.now()
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(
            f"{recorded_at.isoformat(timespec='seconds')} {message}\n"
        )
