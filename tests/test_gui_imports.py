import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


class GuiImportTests(unittest.TestCase):
    def test_production_dialog_imports_before_gui_entry_point(self):
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join((str(SRC), str(ROOT)))
        environment["QT_QPA_PLATFORM"] = "offscreen"
        command = (
            "from ui import all_test_dialog; "
            "from configuration import test_parameters; import GUI; "
            "assert GUI.AllTestMeasurement is all_test_dialog.AllTestMeasurement; "
            "assert GUI.Parameters is test_parameters.Parameters"
        )

        result = subprocess.run(
            [sys.executable, "-c", command],
            capture_output=True,
            text=True,
            env=environment,
            timeout=30,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
