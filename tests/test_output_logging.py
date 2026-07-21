import datetime
import sys
import tempfile
import unittest
from io import BytesIO, TextIOWrapper
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from common.output_logging import append_timestamped_line, print_console_safe


class OutputLoggingTests(unittest.TestCase):
    def test_console_output_supports_print_arguments_and_cp1252(self):
        raw_stream = BytesIO()
        stream = TextIOWrapper(raw_stream, encoding="cp1252")

        print_console_safe("✅", "complete", sep=": ", stream=stream, flush=True)

        self.assertEqual(
            raw_stream.getvalue().decode("cp1252").strip(),
            "?: complete",
        )

    def test_append_timestamped_line_creates_utf8_log(self):
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "logs" / "run.log"
            append_timestamped_line(
                log_path,
                "Measurement ✅",
                timestamp=datetime.datetime(2026, 7, 16, 10, 30, 0),
            )
            content = log_path.read_text(encoding="utf-8")

        self.assertEqual(content, "2026-07-16T10:30:00 Measurement ✅\n")


if __name__ == "__main__":
    unittest.main()
