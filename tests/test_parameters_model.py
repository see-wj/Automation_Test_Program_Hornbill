import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for import_path in (SRC, ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from PyQt5.QtWidgets import QApplication

import GUI
from configuration.test_parameters import Parameters


class ParametersModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_gui_reexports_production_parameters(self):
        self.assertIs(GUI.Parameters, Parameters)

    def test_parameters_support_mapping_access(self):
        parameters = Parameters()

        parameters["noofloop"] = "3"

        self.assertEqual(parameters["noofloop"], "3")
        self.assertEqual(parameters.get("missing", "fallback"), "fallback")


if __name__ == "__main__":
    unittest.main()
