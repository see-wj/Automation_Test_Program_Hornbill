import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class RunStorage:
    root: Path
    raw: Path
    charts: Path
    reports: Path
    logs: Path
    log_file: Path
    diagnostics_file: Path


def _safe_name(value):
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "DUT")).strip("_")
    return cleaned or "DUT"


def create_run_storage(base_directory, dut_name, started_at=None):
    started_at = started_at or datetime.now()
    timestamp = started_at.strftime("%Y%m%d_%H%M%S_%f")
    root = Path(base_directory) / f"{timestamp}_{_safe_name(dut_name)}"
    raw = root / "raw"
    charts = root / "charts"
    reports = root / "reports"
    logs = root / "logs"

    for directory in (raw, charts, reports, logs):
        directory.mkdir(parents=True, exist_ok=False)

    log_file = logs / "run.log"
    diagnostics_file = logs / "diagnostics.jsonl"
    log_file.write_text(
        f"Run created: {started_at.isoformat()}\nDUT: {dut_name}\n",
        encoding="utf-8",
    )
    diagnostics_file.touch()
    return RunStorage(
        root, raw, charts, reports, logs, log_file, diagnostics_file
    )
