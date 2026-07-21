import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for import_path in (SRC, ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from PyQt5.QtWidgets import QApplication

from ui.test_queue_widget import TestQueueWidget
from execution.test_run_controller import TestRunRequest


class TestQueueWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_selected_row_emits_duplicate_retry_and_template_actions(self):
        widget = TestQueueWidget()
        request = TestRunRequest({}, {"DUT": "Dolphin"}, {}, run_id="run-1")
        widget.add_request(request)
        widget.table.selectRow(0)
        duplicated = []
        retried = []
        saved = []
        loaded = []
        widget.duplicate_requested.connect(duplicated.append)
        widget.retry_requested.connect(retried.append)
        widget.save_template_requested.connect(lambda: saved.append(True))
        widget.load_template_requested.connect(lambda: loaded.append(True))

        widget.duplicate_button.click()
        widget.retry_button.click()
        widget.save_template_button.click()
        widget.load_template_button.click()

        self.assertEqual(duplicated, ["run-1"])
        self.assertEqual(retried, ["run-1"])
        self.assertEqual(saved, [True])
        self.assertEqual(loaded, [True])
        widget.remove_run("run-1")
        self.assertEqual(widget.table.rowCount(), 0)
        widget.deleteLater()
        self.application.processEvents()


if __name__ == "__main__":
    unittest.main()
