import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for import_path in (SRC, ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from queueing.queue_template_service import append_queue_template, save_queue_template
from execution.test_run_controller import TestRunController


class QueueTemplateServiceTests(unittest.TestCase):
    def test_template_appends_fresh_request_ids_and_parameter_snapshots(self):
        source = TestRunController()
        source_request = source.enqueue(
            {"Voltage_Test": True},
            {"DUT": "Dolphin"},
            {"noofloop": "3"},
            label="Reusable voltage test",
            auto_start=False,
        )

        with tempfile.TemporaryDirectory() as directory:
            template_path = Path(directory) / "queue-template.json"
            save_queue_template(template_path, source.pending_requests)
            destination = TestRunController()
            loaded_count = append_queue_template(template_path, destination)

        loaded = destination.pending_requests[0]
        self.assertEqual(loaded_count, 1)
        self.assertNotEqual(loaded.run_id, source_request.run_id)
        self.assertEqual(loaded.label, "Reusable voltage test")
        self.assertEqual(loaded.parameters.noofloop, "3")


if __name__ == "__main__":
    unittest.main()
