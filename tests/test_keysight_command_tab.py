import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for import_path in (SRC, ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from PyQt5.QtWidgets import QApplication

from ui.keysight_command_tab import (
    KeysightCommandTab,
    error_query_for,
    format_checked_result,
    format_method_result,
    preview_method,
    query_instrument_error,
    query_system_error,
)
from SCPI_Library.Keysight import DMM_3458A, Hornbill


class KeysightCommandTabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tab = KeysightCommandTab()

    def tearDown(self):
        self.tab.close()
        self.tab.deleteLater()
        self.application.processEvents()

    def _select_method(self, class_name, method_name, **arguments):
        self.tab.class_combo.setCurrentText(class_name)
        self.tab.method_combo.setCurrentText(method_name)
        for parameter, input_widget in self.tab.argument_inputs:
            if parameter.name in arguments:
                input_widget.setText(str(arguments[parameter.name]))

    def test_lists_keysight_classes_and_methods(self):
        self.assertIn("Hornbill", self.tab.instrument_classes)

        self.tab.class_combo.setCurrentText("Hornbill")

        methods = {
            self.tab.method_combo.itemText(index)
            for index in range(self.tab.method_combo.count())
        }
        self.assertIn("measureVoltageDC", methods)
        self.assertIn("measureReadbackCurrent", methods)

    def test_selecting_hornbill_automatically_builds_complete_command_catalog(self):
        self.tab.class_combo.setCurrentText("Hornbill")

        rows = {
            self.tab.command_table.item(row, 0).text(): {
                "command": self.tab.command_table.item(row, 2).text(),
                "status": self.tab.command_table.item(row, 3).text(),
            }
            for row in range(self.tab.command_table.rowCount())
        }

        self.assertEqual(len(rows), 26)
        self.assertIn("measureVoltageDC", rows)
        self.assertIn("MEAS:VOLT:DC? (@1)", rows["measureVoltageDC"]["command"])
        self.assertIn("DIAG:PEEK? 20,0,100000", rows["measureReadbackVoltage"]["command"])
        self.assertTrue(all(item["status"] == "Ready" for item in rows.values()))

    def test_automatic_hardware_jobs_include_only_query_methods(self):
        self.tab.class_combo.setCurrentText("Hornbill")

        method_names = {name for name, _ in self.tab.query_catalog_jobs()}

        self.assertIn("measureCurrentDC", method_names)
        self.assertIn("measureReadbackVoltage", method_names)
        self.assertNotIn("outputState", method_names)
        self.assertIn("measureVoltageDC", method_names)

    def test_catalog_search_filters_methods_and_commands(self):
        self.tab.class_combo.setCurrentText("Hornbill")
        self.tab.search_input.setText("MEAS:ARR:VOLT")

        visible_methods = {
            self.tab.command_table.item(row, 0).text()
            for row in range(self.tab.command_table.rowCount())
            if not self.tab.command_table.isRowHidden(row)
        }

        self.assertEqual(visible_methods, {"measureVoltageArray"})

    def test_preview_records_generated_scpi_without_hardware(self):
        self._select_method(
            "Hornbill",
            "measureVoltageDC",
            ChannelNumber=1,
        )

        self.tab.run_selected_method()

        output = self.tab.output.toPlainText()
        self.assertIn("QUERY: MEAS:VOLT:DC? (@1)", output)
        self.assertIn("QUERY: SYST:ERR?", output)

    def test_execute_mode_requires_safety_acknowledgement(self):
        self._select_method("Hornbill", "outputState", state="ON", ChannelNumber=1)
        self.tab.mode_combo.setCurrentText(self.tab.EXECUTE_MODE)

        with patch("ui.keysight_command_tab.QMessageBox.warning") as warning:
            self.tab.run_selected_method()

        warning.assert_called_once()
        self.assertIsNone(self.tab.worker)

    def test_loads_configured_hostname_and_gpib_addresses(self):
        addresses = {
            self.tab.address_combo.itemText(index)
            for index in range(self.tab.address_combo.count())
        }

        self.assertIn("TCPIP0::p700-95640339::inst0::INSTR", addresses)
        self.assertIn("GPIB0::22::INSTR", addresses)

    def test_formats_write_only_result_as_success(self):
        self.assertEqual(
            format_method_result(None),
            "Command sent successfully (write-only; no instrument response expected).",
        )

    def test_preserves_query_result_value(self):
        self.assertEqual(format_method_result(12.5), "Result: 12.5")

    def test_system_error_check_accepts_no_error_response(self):
        instrument = type(
            "Instrument",
            (),
            {"query": lambda self, command: '+0,"No error"'},
        )()

        self.assertEqual(query_system_error(instrument), '+0,"No error"')

    def test_system_error_check_rejects_instrument_error(self):
        instrument = type(
            "Instrument",
            (),
            {"query": lambda self, command: '-113,"Undefined header"'},
        )()

        with self.assertRaisesRegex(RuntimeError, "Undefined header"):
            query_system_error(instrument)

    def test_3458a_uses_legacy_error_query(self):
        self.assertEqual(error_query_for(DMM_3458A), "ERR?")
        self.assertEqual(error_query_for(Hornbill), "SYST:ERR?")

        commands, _ = preview_method(DMM_3458A, "queryMeasurement", [])

        self.assertEqual(commands[-1], ("query", "ERR?"))

    def test_3458a_error_check_sends_err_query(self):
        commands = []
        instrument = type(
            "Instrument",
            (),
            {"query": lambda self, command: commands.append(command) or "0"},
        )()

        self.assertEqual(query_instrument_error(instrument, DMM_3458A), "0")
        self.assertEqual(commands, ["ERR?"])

    def test_checked_result_includes_method_and_system_error(self):
        self.assertEqual(
            format_checked_result("1.25", '+0,"No error"'),
            'Result: \'1.25\'\nSYST:ERR?: +0,"No error"',
        )

    def test_checked_result_labels_3458a_error_query(self):
        self.assertEqual(
            format_checked_result("1.25", "0", "ERR?"),
            "Result: '1.25'\nERR?: 0",
        )


if __name__ == "__main__":
    unittest.main()
