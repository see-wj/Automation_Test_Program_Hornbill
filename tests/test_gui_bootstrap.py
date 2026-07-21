import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class GuiBootstrapTests(unittest.TestCase):
    def test_native_visa_initializes_before_any_qt_import(self):
        source = (ROOT / "src" / "GUI.py").read_text(encoding="utf-8")

        visa_initialization = source.index(
            "    main_thread_resource_manager = initialize_main_thread_visa()"
        )
        pyqtgraph_import = source.index("import pyqtgraph")
        pyqt_import = source.index("from PyQt5")

        self.assertLess(visa_initialization, pyqtgraph_import)
        self.assertLess(visa_initialization, pyqt_import)

    def test_packaged_runtime_hook_initializes_visa_before_entry_point(self):
        hook = (
            ROOT / "packaging_hooks" / "initialize_native_visa.py"
        ).read_text(encoding="utf-8")
        build_script = (ROOT / "Make_GUI_Executable_Program.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("initialize_main_thread_visa()", hook)
        self.assertIn("--runtime-hook=", build_script)

    def test_gui_exposes_frozen_visa_diagnostics_mode(self):
        source = (ROOT / "src" / "GUI.py").read_text(encoding="utf-8")

        self.assertIn('"--visa-diagnostics" in sys.argv', source)
        self.assertIn("main_thread_resource_manager.visalib", source)
        self.assertIn('gpib_instrument.write("ID?")', source)


if __name__ == "__main__":
    unittest.main()
