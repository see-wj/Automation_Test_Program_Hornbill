import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for import_path in (SRC, ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from queueing.queue_persistence import QueuePersistence, QueuePersistenceError
from configuration.test_configuration import ParameterSnapshot
from execution.test_run_controller import TestRunRequest


class QueuePersistenceTests(unittest.TestCase):
    def test_round_trip_preserves_pending_request(self):
        with tempfile.TemporaryDirectory() as directory:
            persistence = QueuePersistence(Path(directory) / "queue.json")
            request = TestRunRequest(
                {"Voltage_Test": True},
                {"DUT": "Dolphin"},
                ParameterSnapshot(noofloop="2"),
                label="Dolphin voltage",
                run_id="run-1",
            )

            persistence.save([request])
            restored = persistence.load()

        self.assertEqual(restored[0]["run_id"], "run-1")
        self.assertEqual(restored[0]["parameters"]["noofloop"], "2")

    def test_save_replaces_previous_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "queue.json"
            persistence = QueuePersistence(path)
            persistence.save([])
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["pending"], [])

    def test_round_trip_preserves_active_and_interrupted_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "queue.json"
            persistence = QueuePersistence(path)
            active_parameters = ParameterSnapshot(
                noofloop="1",
                savelocation="runtime/reports",
                run_context=SimpleNamespace(
                    storage=SimpleNamespace(root=Path("runtime/run-1")),
                    output_root=Path("original-output"),
                ),
            )
            active = TestRunRequest(
                {"Voltage_Test": True},
                {"DUT": "Dolphin"},
                active_parameters,
                label="Active voltage",
                run_id="active-1",
            )
            interrupted = TestRunRequest(
                {"Current_Test": True},
                {"DUT": "Hornbill"},
                ParameterSnapshot(noofloop="2"),
                label="Interrupted current",
                run_id="interrupted-1",
                recovery_run_directory="previous/run-2",
            )

            persistence.save([], active, [interrupted])
            snapshot = persistence.load_snapshot()

        self.assertEqual(snapshot["active"]["run_id"], "active-1")
        self.assertEqual(
            Path(snapshot["active"]["run_directory"]),
            Path("runtime/run-1"),
        )
        self.assertEqual(
            snapshot["active"]["parameters"]["savelocation"],
            "original-output",
        )
        self.assertNotIn("run_context", snapshot["active"]["parameters"])
        self.assertEqual(
            snapshot["interrupted"][0]["run_directory"],
            "previous/run-2",
        )

    def test_load_snapshot_migrates_version_one_pending_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "queue.json"
            path.write_text(
                json.dumps({"schema_version": 1, "pending": [{"run_id": "old"}]}),
                encoding="utf-8",
            )

            snapshot = QueuePersistence(path).load_snapshot()

        self.assertEqual(snapshot["pending"], [{"run_id": "old"}])
        self.assertIsNone(snapshot["active"])
        self.assertEqual(snapshot["interrupted"], [])

    def test_invalid_json_reports_clear_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "queue.json"
            path.write_text("not-json", encoding="utf-8")

            with self.assertRaises(QueuePersistenceError):
                QueuePersistence(path).load()


if __name__ == "__main__":
    unittest.main()
