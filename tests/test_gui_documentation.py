import os
import sys
import tempfile
import unittest
from pathlib import Path


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for import_path in (SRC, ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from PyQt5.QtWidgets import QApplication

import GUI
from ui.documentation_tab import (
    ProgramDocumentationTab,
    TestPatternsTab,
    build_hornbill_voltage_accuracy_patterns,
    build_remaining_test_patterns,
)
from ui.keysight_command_tab import KeysightCommandTab


class GuiDocumentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_tab(self):
        tab = ProgramDocumentationTab()
        self.addCleanup(self.dispose_widget, tab)
        return tab

    def dispose_widget(self, widget):
        widget.close()
        widget.deleteLater()
        self.app.processEvents()

    def test_documentation_covers_operator_and_developer_workflows(self):
        tab = self.make_tab()
        content = tab.browser.toPlainText()

        self.assertIn("Quick Start", content)
        self.assertIn("Hardware safety", content)
        self.assertIn("Adding a New Standalone Test Dialog", content)
        self.assertIn("Adding a New Bundle Test Script", content)
        self.assertIn("Calibration is work in progress", content)
        self.assertIn("VI_ERROR_LIBRARY_NFOUND", content)

    def test_documentation_search_wraps_to_first_match(self):
        tab = self.make_tab()
        tab.browser.moveCursor(tab.browser.textCursor().End)
        tab.search_input.setText("Quick Start")

        self.assertTrue(tab.find_next())
        self.assertEqual(tab.browser.textCursor().selectedText(), "Quick Start")

    def test_dedicated_tab_shows_real_voltage_accuracy_patterns(self):
        tab = TestPatternsTab()
        self.addCleanup(self.dispose_widget, tab)

        static_curves = tab.pattern_graphs.current_static_plot.listDataItems()
        changing_curves = tab.pattern_graphs.current_change_plot.listDataItems()

        self.assertEqual(len(static_curves), 2)
        self.assertEqual(len(changing_curves), 2)
        self.assertEqual(static_curves[0].name(), "PSU Voltage (V)")
        self.assertEqual(static_curves[1].name(), "ELoad Current (A)")
        self.assertEqual(tab.category_tabs.count(), 5)
        self.assertEqual(
            [tab.category_tabs.tabText(index) for index in range(5)],
            ["Accuracy", "Regulation", "Dynamic", "Protection", "Power"],
        )

    def test_remaining_production_patterns_are_available(self):
        patterns = build_remaining_test_patterns()

        self.assertEqual(
            set(patterns),
            {
                "current_accuracy",
                "voltage_load_regulation",
                "current_load_regulation",
                "transient_recovery",
                "transient_special",
                "programming_response",
                "line_regulation",
                "power_accuracy",
                "ovp",
                "ocp",
            },
        )
        self.assertEqual(
            patterns["power_accuracy"]["series"][0][1],
            list(range(0, 310, 10)),
        )
        self.assertEqual(
            patterns["voltage_load_regulation"]["series"][0][1],
            [60.0, 60.0, 0, 15.0, 15.0],
        )
        self.assertEqual(patterns["ocp"]["x"], [0, 1, 9, 10, 10.1, 12])
        self.assertEqual(
            patterns["transient_special"]["series"][1][1][:3],
            [0, 5.0, 0],
        )

    def test_hornbill_patterns_match_nested_test_script_loops(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config_Hornbill.txt"
            config_path.write_text(
                "\n".join(
                    (
                        "minVoltage = 3",
                        "maxVoltage = 60",
                        "voltage_step_size = 3",
                        "minCurrent = 0",
                        "maxCurrent = 20",
                        "current_step_size = 5",
                        "Power = 300",
                    )
                ),
                encoding="utf-8",
            )
            patterns = build_hornbill_voltage_accuracy_patterns(config_path)
        static = patterns["current_static"]
        changing = patterns["current_change"]

        self.assertEqual(static["voltage"][:4], [3.0, 6.0, 9.0, 12.0])
        self.assertEqual(static["current"][:4], [0.0, 0.0, 0.0, 0.0])
        self.assertEqual(static["voltage"][20:24], [3.0, 6.0, 9.0, 12.0])
        self.assertEqual(static["current"][20:24], [5.0, 5.0, 5.0, 5.0])
        self.assertEqual(changing["voltage"][:5], [3.0] * 5)
        self.assertEqual(
            changing["current"][:5],
            [0, 4.999, 9.999, 14.999, 19.9],
        )
        maximum_load_voltages = [
            voltage
            for voltage, current in zip(static["voltage"], static["current"])
            if current == 19.9
        ]
        self.assertEqual(maximum_load_voltages, [3.0, 6.0, 9.0, 12.0, 15.0])
        self.assertEqual(changing["voltage"][-1], 60.0)
        self.assertEqual(changing["current"][-1], 4.999)

    def test_main_window_separates_documentation_and_test_patterns(self):
        window = GUI.MainWindow()
        self.addCleanup(self.dispose_widget, window)

        self.assertEqual(window.tab_widget.count(), 6)
        self.assertEqual(window.tab_widget.tabText(3), "Documentation")
        self.assertIsInstance(window.tab_widget.widget(3), ProgramDocumentationTab)
        self.assertEqual(window.tab_widget.tabText(4), "Test Patterns")
        self.assertIsInstance(window.tab_widget.widget(4), TestPatternsTab)
        self.assertEqual(window.tab_widget.tabText(5), "Keysight Commands")
        self.assertIsInstance(window.tab_widget.widget(5), KeysightCommandTab)
        self.assertFalse(hasattr(window.tab_Documentation, "pattern_graphs"))

        window.tab_widget.setCurrentIndex(3)
        self.assertTrue(window.QButton_Widget.isHidden())
        window.tab_widget.setCurrentIndex(4)
        self.assertTrue(window.QButton_Widget.isHidden())
        window.tab_widget.setCurrentIndex(5)
        self.assertTrue(window.QButton_Widget.isHidden())
        window.tab_widget.setCurrentIndex(0)
        self.assertFalse(window.QButton_Widget.isHidden())


if __name__ == "__main__":
    unittest.main()
