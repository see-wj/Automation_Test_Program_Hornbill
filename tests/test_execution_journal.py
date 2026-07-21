import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for import_path in (SRC, ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import GUI
from execution.execution_journal import ExecutionJournal, JOURNAL_FILE_NAME
from SCPI_Library.simulation import reset_simulation


class ExecutionJournalTests(unittest.TestCase):
    def test_completed_loop_is_loaded_by_followup_run(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = Path(directory) / "previous"
            current = Path(directory) / "current"
            previous_context = SimpleNamespace(
                storage=SimpleNamespace(logs=previous / "logs")
            )
            current_context = SimpleNamespace(
                storage=SimpleNamespace(logs=current / "logs")
            )
            first = ExecutionJournal.for_run(previous_context)
            first.complete_loop(1)

            resumed = ExecutionJournal.for_run(current_context, previous)

        self.assertEqual(resumed.next_loop_index, 2)
        self.assertEqual(resumed.resumed_from, str(previous))

    def test_invalid_previous_journal_restarts_from_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "logs" / JOURNAL_FILE_NAME
            path.parent.mkdir(parents=True)
            path.write_text("invalid", encoding="utf-8")

            self.assertEqual(ExecutionJournal.load_next_loop(path), 0)

    def test_worker_skips_only_completed_loops(self):
        reset_simulation()
        with tempfile.TemporaryDirectory() as directory:
            previous = Path(directory) / "previous"
            previous_log = previous / "logs" / JOURNAL_FILE_NAME
            previous_log.parent.mkdir(parents=True)
            previous_log.write_text(
                json.dumps({"schema_version": 1, "next_loop_index": 2}),
                encoding="utf-8",
            )
            current_logs = Path(directory) / "current" / "logs"
            run_context = SimpleNamespace(
                storage=SimpleNamespace(logs=current_logs),
                activate_data_paths=lambda: None,
            )
            parameters = GUI.ParameterSnapshot(
                DUT="Dolphin",
                noofloop=4,
                resume_run_directory=str(previous),
                run_context=run_context,
            )
            worker = GUI.TestWorker({}, parameters, parameters)
            dispatched = []
            worker._dispatch_dut_tests = dispatched.append

            with patch.object(worker, "safe_shutdown"), patch.object(
                worker, "close_visa_sessions"
            ), patch("execution.test_worker.begin_visa_session_scope"):
                worker.run()

        self.assertEqual(dispatched, [2, 3])
        self.assertEqual(worker.execution_journal.next_loop_index, 4)


if __name__ == "__main__":
    unittest.main()
