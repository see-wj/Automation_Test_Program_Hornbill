import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for import_path in (SRC, ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from PyQt5.QtWidgets import QApplication

from ui.webcam_widget import WebcamWidget


class WebcamWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_preview_is_idle_by_default(self):
        widget = WebcamWidget()
        self.assertFalse(widget.preview_active)
        self.assertFalse(widget.stop_button.isEnabled())
        self.assertEqual(widget.resolution_selector.currentData(), (1280, 720))
        widget.close()

    def test_stop_preview_is_safe_when_already_stopped(self):
        widget = WebcamWidget()
        widget.stop_preview()
        self.assertFalse(widget.preview_active)
        widget.close()


if __name__ == "__main__":
    unittest.main()
